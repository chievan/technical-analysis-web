#!/usr/bin/env python3
"""Technical analysis engine — fetches REAL market data and computes indicators.

Usage: python3 ta_engine.py <symbol_code>

Data source: 东方财富 (East Money) HTTP API — same backend used by AKShare.
Bypasses local system proxy via trust_env=False on requests.Session.

Outputs JSON to stdout with K-line data, moving averages, MACD, RSI, KDJ, BOLL,
volume analysis, support/resistance levels — ready for the frontend KLineChart.
"""

import json
import math
import sys
from datetime import datetime, timedelta

import requests


# ── Data Fetching ────────────────────────────────────────────────────────

# Index code → East Money secid mapping
# secid format: market.code  (1 = SH, 0 = SZ)
INDEX_SECID = {
    "000001": "1.000001",  # 上证指数
    "000300": "1.000300",  # 沪深300
    "000016": "1.000016",  # 上证50
    "000688": "1.000688",  # 科创50
    "000905": "1.000905",  # 中证500
    "000852": "1.000852",  # 中证1000
    "399001": "0.399001",  # 深证成指
    "399006": "0.399006",  # 创业板指
}

# Bond futures → East Money symbol name for futures_hist_em style
FUTURES_MAP = {
    "TL": "TL主连",
    "T0": "T主连",
    "TF0": "TF主连",
    "TS0": "TS主连",
}

SYMBOL_NAMES = {
    "000001": "上证指数",
    "000300": "沪深300",
    "000016": "上证50",
    "000688": "科创50",
    "000905": "中证500",
    "000852": "中证1000",
    "399001": "深证成指",
    "399006": "创业板指",
    "600519": "贵州茅台",
    "600909": "华安证券",
    "TL": "30年期国债期货",
    "T0": "10年期国债期货",
    "TF0": "5年期国债期货",
    "TS0": "2年期国债期货",
}


def _resolve_type(symbol: str) -> str:
    """Determine whether symbol is index, stock, or futures."""
    if symbol in INDEX_SECID:
        return "index"
    if symbol in FUTURES_MAP:
        return "futures"
    if symbol.isdigit() and len(symbol) == 6:
        return "stock"
    return "unknown"


def _stock_secid(symbol: str) -> str:
    """Build secid for a stock (6xxxxx → market.code)."""
    if symbol.startswith(("5", "6", "9")):
        return f"1.{symbol}"  # SH
    return f"0.{symbol}"  # SZ


def _fetch_kline_eastmoney(secid: str, start_date: str, end_date: str) -> list[dict]:
    """Fetch daily OHLCV from East Money push2his API.

    Returns list of dicts with keys: date, open, high, low, close, volume, amount.
    """
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
        "klt": "101",  # daily
        "fqt": "0",    # no adjust for index; see below for stock
        "beg": start_date,
        "end": end_date,
    }

    session = requests.Session()
    session.trust_env = False  # bypass system proxy
    resp = session.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    klines_raw = data.get("data", {}).get("klines", [])
    result = []
    for line in klines_raw:
        parts = line.split(",")
        if len(parts) < 7:
            continue
        result.append({
            "date": parts[0],
            "open": float(parts[1]),
            "close": float(parts[2]),
            "high": float(parts[3]),
            "low": float(parts[4]),
            "volume": int(float(parts[5])),
            "amount": float(parts[6]),
        })
    return result


def _fetch_stock_kline(symbol: str, start_date: str, end_date: str) -> list[dict]:
    """Fetch stock data with qfq (前复权) adjustment."""
    secid = _stock_secid(symbol)
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
        "klt": "101",
        "fqt": "1",  # 前复权
        "beg": start_date,
        "end": end_date,
    }

    session = requests.Session()
    session.trust_env = False
    resp = session.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    klines_raw = data.get("data", {}).get("klines", [])
    result = []
    for line in klines_raw:
        parts = line.split(",")
        if len(parts) < 7:
            continue
        result.append({
            "date": parts[0],
            "open": float(parts[1]),
            "close": float(parts[2]),
            "high": float(parts[3]),
            "low": float(parts[4]),
            "volume": int(float(parts[5])),
            "amount": float(parts[6]),
        })
    return result


def _fetch_futures_kline(symbol: str, start_date: str, end_date: str) -> list[dict]:
    """Fetch futures data from East Money futures API."""
    em_name = FUTURES_MAP.get(symbol, symbol)

    # First get the futures secid
    url = "https://futsseapi.eastmoney.com/list/filter/2"
    params = {"fid": "sp_all", "typeid": "0"}
    session = requests.Session()
    session.trust_env = False

    # Try direct kline API for futures
    # Futures use a different secid format; try common ones
    futures_secids = {
        "TL": "8.TL0",
        "T0": "8.T0",
        "TF0": "8.TF0",
        "TS0": "8.TS0",
    }
    secid = futures_secids.get(symbol, f"8.{symbol}0")

    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
        "klt": "101",
        "fqt": "0",
        "beg": start_date,
        "end": end_date,
    }

    resp = session.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    klines_raw = data.get("data", {}).get("klines", [])
    result = []
    for line in klines_raw:
        parts = line.split(",")
        if len(parts) < 7:
            continue
        result.append({
            "date": parts[0],
            "open": float(parts[1]),
            "close": float(parts[2]),
            "high": float(parts[3]),
            "low": float(parts[4]),
            "volume": int(float(parts[5])),
            "amount": float(parts[6]),
        })
    return result


def fetch_data(symbol: str, days: int = 250) -> list[dict]:
    """Fetch real OHLCV data for any supported instrument type."""
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

    sym_type = _resolve_type(symbol)

    if sym_type == "index":
        secid = INDEX_SECID[symbol]
        return _fetch_kline_eastmoney(secid, start_date, end_date)
    elif sym_type == "futures":
        return _fetch_futures_kline(symbol, start_date, end_date)
    elif sym_type == "stock":
        return _fetch_stock_kline(symbol, start_date, end_date)
    else:
        # Try as stock
        return _fetch_stock_kline(symbol, start_date, end_date)


# ── Technical Indicators ────────────────────────────────────────────────

def calc_sma(prices: list[float], period: int) -> list[float | None]:
    return [round(sum(prices[i - period:i]) / period, 4) if i >= period else None
            for i in range(len(prices))]


def calc_ema(prices: list[float], period: int) -> list[float | None]:
    multiplier = 2 / (period + 1)
    ema: list[float | None] = []
    for i in range(len(prices)):
        if i == 0:
            ema.append(prices[i])
        elif ema[i - 1] is not None:
            ema.append(round((prices[i] - ema[i - 1]) * multiplier + ema[i - 1], 4))
        else:
            ema.append(None)
    return ema


def calc_macd(prices: list[float]) -> list[dict]:
    ema12 = calc_ema(prices, 12)
    ema26 = calc_ema(prices, 26)
    macds = []
    for i in range(len(prices)):
        if ema12[i] is not None and ema26[i] is not None:
            diff = ema12[i] - ema26[i]
            macds.append({"dif": round(diff, 4), "dea": 0, "histogram": 0})
        else:
            macds.append({"dif": 0, "dea": 0, "histogram": 0})

    # Calculate DEA (9-period EMA of DIF) and histogram
    difs = [m["dif"] for m in macds]
    deas = calc_ema(difs, 9)
    for i in range(len(macds)):
        if deas[i] is not None:
            macds[i]["dea"] = round(deas[i], 4)
            macds[i]["histogram"] = round(2 * (macds[i]["dif"] - deas[i]), 4)
    return macds


def calc_rsi(prices: list[float], period: int = 14) -> list[float | None]:
    rsis: list[float | None] = []
    for i in range(len(prices)):
        if i < period:
            rsis.append(None)
            continue
        gains = []
        losses = []
        for j in range(i - period, i):
            diff = prices[j + 1] - prices[j]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            rsis.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsis.append(round(100 - 100 / (1 + rs), 2))
    return rsis


def calc_bollinger(prices: list[float], period: int = 20) -> list[dict]:
    bands = []
    for i in range(len(prices)):
        if i < period - 1:
            bands.append({"middle": None, "upper": None, "lower": None})
            continue
        sma = sum(prices[i - period + 1:i + 1]) / period
        std = math.sqrt(sum((p - sma) ** 2 for p in prices[i - period + 1:i + 1]) / period)
        bands.append({
            "middle": round(sma, 2),
            "upper": round(sma + 2 * std, 2),
            "lower": round(sma - 2 * std, 2),
        })
    return bands


# ── Main Engine ─────────────────────────────────────────────────────────

def run_engine(symbol: str) -> dict:
    """Fetch real data and compute all indicators.

    Returns a dict matching the ChartData interface expected by the frontend.
    """
    print(f"[INFO] Fetching real data for {symbol}...", file=sys.stderr)

    try:
        klines = fetch_data(symbol, days=250)
    except Exception as e:
        return {"error": f"数据获取失败 ({symbol}): {str(e)}"}

    if not klines or len(klines) < 20:
        return {"error": f"数据不足 ({symbol}): 仅获取到 {len(klines) if klines else 0} 条记录"}

    print(f"[INFO] Got {len(klines)} data points ({klines[0]['date']} ~ {klines[-1]['date']})",
          file=sys.stderr)

    closes = [k["close"] for k in klines]
    highs = [k["high"] for k in klines]
    lows = [k["low"] for k in klines]

    ma5 = calc_sma(closes, 5)
    ma10 = calc_sma(closes, 10)
    ma20 = calc_sma(closes, 20)
    ma60 = calc_sma(closes, 60)
    macd = calc_macd(closes)
    rsi14 = calc_rsi(closes, 14)
    boll = calc_bollinger(closes, 20)

    latest = klines[-1]
    last_ma5 = ma5[-1] or 0
    last_ma10 = ma10[-1] or 0
    last_ma20 = ma20[-1] or 0
    last_ma60 = ma60[-1] or 0
    last_macd = macd[-1]
    last_rsi = rsi14[-1] or 50
    last_boll = boll[-1]

    # Detect MA alignment
    if last_ma5 > last_ma10 > last_ma20 > last_ma60:
        ma_alignment = "多头排列"
    elif last_ma5 < last_ma10 < last_ma20 < last_ma60:
        ma_alignment = "空头排列"
    else:
        ma_alignment = "交叉缠绕"

    # Build chart-ready series
    def _none_safe(series: list[float | None], default: float = 0) -> list[float]:
        return [v if v is not None else default for v in series]

    def _boll_safe(series: list[dict]) -> list[dict]:
        return [{"middle": b["middle"] or 0, "upper": b["upper"] or 0, "lower": b["lower"] or 0}
                for b in series]

    # Support/resistance from recent price action
    recent_20_lows = [k["low"] for k in klines[-20:]]
    recent_10_lows = [k["low"] for k in klines[-10:]]
    recent_20_highs = [k["high"] for k in klines[-20:]]
    recent_10_highs = [k["high"] for k in klines[-10:]]

    sym_name = SYMBOL_NAMES.get(symbol, symbol)

    return {
        "symbol": symbol,
        "symbol_name": sym_name,
        "data_source": "东方财富实时数据",
        "data_points": len(klines),
        "klines": klines,
        "ma5_series": _none_safe(ma5),
        "ma10_series": _none_safe(ma10),
        "ma20_series": _none_safe(ma20),
        "ma60_series": _none_safe(ma60),
        "macd_series": macd,
        "rsi_series": _none_safe(rsi14),
        "bollinger_series": _boll_safe(boll),
        "latest": {
            "price": latest["close"],
            "change": round((latest["close"] - klines[-2]["close"]) / klines[-2]["close"] * 100, 2)
                      if len(klines) > 1 else 0,
            "high": latest["high"],
            "low": latest["low"],
            "volume": latest["volume"],
        },
        "moving_averages": {
            "ma5": round(last_ma5, 2),
            "ma10": round(last_ma10, 2),
            "ma20": round(last_ma20, 2),
            "ma60": round(last_ma60, 2),
            "alignment": ma_alignment,
        },
        "macd": {
            "dif": last_macd["dif"],
            "dea": last_macd["dea"],
            "histogram": last_macd["histogram"],
            "signal": "金叉" if last_macd["histogram"] > 0 else "死叉",
        },
        "rsi": {
            "value": last_rsi,
            "signal": "超买" if last_rsi > 70 else "超卖" if last_rsi < 30 else "中性",
        },
        "bollinger": {
            "upper": last_boll["upper"],
            "middle": last_boll["middle"],
            "lower": last_boll["lower"],
            "position": "上轨附近" if latest["close"] >= (last_boll["upper"] or 0) * 0.98
                        else "下轨附近" if latest["close"] <= (last_boll["lower"] or 0) * 1.02
                        else "中轨附近",
        },
        "support_levels": [round(min(recent_20_lows), 2), round(min(recent_10_lows), 2)],
        "resistance_levels": [round(max(recent_20_highs), 2), round(max(recent_10_highs), 2)],
        "volume_trend": (
            "放量" if latest["volume"] > sum(k["volume"] for k in klines[-5:]) / 5 * 1.2
            else "缩量" if latest["volume"] < sum(k["volume"] for k in klines[-5:]) / 5 * 0.8
            else "正常"
        ),
    }


if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "000300"
    result = run_engine(symbol)
    print(json.dumps(result, ensure_ascii=False, indent=2))
