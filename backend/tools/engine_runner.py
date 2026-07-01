"""Tool execution functions for the DeepSeek agent.

Each function corresponds to a tool in tool_definitions.py.
Called by agent_service.py when the model requests a tool execution.
"""

import json
import subprocess

from backend.config import SKILL_DIR


def _calc_sma(prices: list[float], period: int) -> list[float | None]:
    """Simple moving average helper — used by run_backtester."""
    result: list[float | None] = []
    for i in range(len(prices)):
        if i < period:
            result.append(None)
        else:
            result.append(sum(prices[i - period : i]) / period)
    return result


def run_ta_engine(code: str) -> dict:
    """Execute ta_engine.py as a subprocess and return parsed JSON output.

    The engine script lives at backend/skill/scripts/ta_engine.py and is a copy
    from the technical-analysis-pro skill repo. If absent, returns an error dict.
    """
    engine_path = SKILL_DIR / "scripts" / "ta_engine.py"
    if not engine_path.exists():
        return {"error": f"引擎脚本不存在: {engine_path}"}

    try:
        result = subprocess.run(
            ["python3", str(engine_path), code],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"引擎执行超时（标的: {code}）"}

    if result.returncode != 0:
        return {
            "error": f"引擎执行失败（返回码 {result.returncode}）: {result.stderr[:500]}"
        }

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return {"error": f"引擎输出解析失败: {str(e)}"}


def read_reference(file: str) -> str:
    """Read a reference document from the skill references directory."""
    ref_path = SKILL_DIR / "references" / file
    if not ref_path.exists():
        available = [p.name for p in (SKILL_DIR / "references").iterdir()] if (SKILL_DIR / "references").exists() else []
        hint = f"可用文档: {available}" if available else "暂无参考文档"
        return f"参考文档 '{file}' 不存在。{hint}"
    return ref_path.read_text(encoding="utf-8")


def run_backtester(
    code: str,
    start_date: str = "",
    end_date: str = "",
    initial_capital: float = 100000,
    strategy: str = "trend_following",
    ma_short: int = 5,
    ma_long: int = 20,
) -> dict:
    """Backtest a trading strategy using historical OHLCV + indicator data.

    Calls ``run_ta_engine(code)`` to obtain K-line data, then simulates
    trading logic for the requested strategy and returns performance metrics.

    Strategies supported:
      - trend_following : MA crossover (golden cross / death cross)
      - mean_reversion  : RSI-based (oversold buy / overbought sell)
    """
    engine_result = run_ta_engine(code)
    if "error" in engine_result:
        return engine_result

    klines = engine_result.get("klines", [])
    if not klines:
        return {"error": "无K线数据"}

    # Filter by date range
    if start_date:
        klines = [k for k in klines if k["date"] >= start_date]
    if end_date:
        klines = [k for k in klines if k["date"] <= end_date]

    if len(klines) < ma_long:
        return {"error": f"数据点不足，至少需要{ma_long}个数据点"}

    closes = [k["close"] for k in klines]
    rsi_series = engine_result.get("rsi_series", [])

    # Calculate custom MAs
    ma_short_series = _calc_sma(closes, ma_short)
    ma_long_series = _calc_sma(closes, ma_long)

    cash = initial_capital
    shares = 0.0
    trades: list[dict] = []
    equity_curve: list[dict] = []
    in_position = False

    for i, k in enumerate(klines):
        date = k["date"]

        if strategy == "mean_reversion":
            # RSI-based mean reversion
            rsi = rsi_series[i] if i < len(rsi_series) and rsi_series[i] is not None else None
            if rsi is not None:
                if rsi < 30 and not in_position and cash > 0:
                    shares = (cash * 0.98) / k["close"]
                    cost = shares * k["close"]
                    cash -= cost
                    trades.append({
                        "date": date, "type": "buy", "price": k["close"],
                        "shares": round(shares, 4), "value": round(cost, 2),
                        "reason": f"RSI={rsi:.1f}<30",
                    })
                    in_position = True
                elif rsi > 70 and in_position and shares > 0:
                    revenue = shares * k["close"]
                    cash += revenue * 0.98
                    trades.append({
                        "date": date, "type": "sell", "price": k["close"],
                        "shares": round(shares, 4), "value": round(revenue, 2),
                        "reason": f"RSI={rsi:.1f}>70",
                    })
                    shares = 0.0
                    in_position = False
        else:
            # Trend following via MA crossover (default)
            if i > 0:
                ps = ma_short_series[i - 1]
                pl = ma_long_series[i - 1]
                cs = ma_short_series[i]
                cl = ma_long_series[i]
                if ps is not None and pl is not None and cs is not None and cl is not None:
                    if ps <= pl and cs > cl and not in_position and cash > 0:
                        # Golden cross -> buy
                        shares = (cash * 0.98) / k["close"]
                        cost = shares * k["close"]
                        cash -= cost
                        trades.append({
                            "date": date, "type": "buy", "price": k["close"],
                            "shares": round(shares, 4), "value": round(cost, 2),
                            "reason": f"MA{ma_short}={cs:.2f}上穿MA{ma_long}={cl:.2f}",
                        })
                        in_position = True
                    elif ps >= pl and cs < cl and in_position and shares > 0:
                        # Death cross -> sell
                        revenue = shares * k["close"]
                        cash += revenue * 0.98
                        trades.append({
                            "date": date, "type": "sell", "price": k["close"],
                            "shares": round(shares, 4), "value": round(revenue, 2),
                            "reason": f"MA{ma_short}={cs:.2f}下穿MA{ma_long}={cl:.2f}",
                        })
                        shares = 0.0
                        in_position = False

        equity_curve.append({
            "date": date,
            "portfolio_value": round(cash + shares * k["close"], 2),
        })

    # Close any remaining position at the last price
    if in_position and shares > 0 and klines:
        last_k = klines[-1]
        revenue = shares * last_k["close"]
        cash += revenue * 0.98
        trades.append({
            "date": last_k["date"], "type": "close", "price": last_k["close"],
            "shares": round(shares, 4), "value": round(revenue, 2),
            "reason": "回测结束平仓",
        })
        shares = 0.0
        equity_curve[-1]["portfolio_value"] = round(cash, 2)

    final_capital = cash
    total_return_pct = round((final_capital - initial_capital) / initial_capital * 100, 2)

    # Max drawdown
    peak = equity_curve[0]["portfolio_value"]
    max_drawdown = 0.0
    for pt in equity_curve:
        v = pt["portfolio_value"]
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100
        if dd > max_drawdown:
            max_drawdown = dd
    max_drawdown_pct = round(max_drawdown, 2)

    # Win rate: count profitable buy-sell cycles
    buy_vals: list[float] = []
    win_count = 0
    total_closed = 0
    for t in trades:
        if t["type"] == "buy":
            buy_vals.append(t["value"])
        elif t["type"] in ("sell", "close"):
            if buy_vals:
                if t["value"] > buy_vals[0]:
                    win_count += 1
                total_closed += 1
                buy_vals.pop(0)

    win_rate = round(win_count / total_closed * 100, 2) if total_closed > 0 else 0.0

    return {
        "symbol": code,
        "symbol_name": engine_result.get("symbol_name", code),
        "initial_capital": initial_capital,
        "final_capital": round(final_capital, 2),
        "total_return_pct": total_return_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "win_rate": win_rate,
        "total_trades": len(trades),
        "trades": trades,
        "equity_curve": equity_curve,
        "parameters": {
            "strategy": strategy,
            "ma_short": ma_short,
            "ma_long": ma_long,
            "start_date": start_date,
            "end_date": end_date,
        },
    }


# Map tool names to execution functions
EXECUTOR_MAP = {
    "run_ta_engine": run_ta_engine,
    "read_reference": read_reference,
    "run_backtester": run_backtester,
}
