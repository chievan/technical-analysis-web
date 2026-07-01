#!/usr/bin/env python3
"""Mock technical analysis engine — returns structured JSON with realistic-looking indicator data.

Usage: python3 ta_engine.py <symbol_code>

Outputs JSON to stdout with K-line data, moving averages, MACD, RSI, KDJ, BOLL, and volume analysis.
This is a stand-in for the real ta_engine.py from the technical-analysis-pro skill.
"""

import json
import math
import random
import sys


def generate_kline(base_price: float, days: int, seed: int) -> list[dict]:
    """Generate realistic OHLCV data using a seeded random walk."""
    rng = random.Random(seed)
    klines = []
    price = base_price

    for i in range(days):
        change = rng.gauss(0, 1.5)
        close = round(price * (1 + change / 100), 2)
        high = round(max(price, close) * (1 + abs(rng.gauss(0, 0.8)) / 100), 2)
        low = round(min(price, close) * (1 - abs(rng.gauss(0, 0.8)) / 100), 2)
        open_price = round(price, 2)
        volume = int(rng.uniform(50000, 500000) * (1 + abs(change) * 3))
        klines.append({
            "date": f"2026-{(i // 30) + 1:02d}-{(i % 30) + 1:02d}",
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        })
        price = close
    return klines


def calc_sma(prices: list[float], period: int) -> list[float | None]:
    return [sum(prices[i - period : i]) / period if i >= period else None for i in range(len(prices))]


def calc_ema(prices: list[float], period: int) -> list[float | None]:
    multiplier = 2 / (period + 1)
    ema: list[float | None] = []
    for i in range(len(prices)):
        if i == 0:
            ema.append(prices[i])
        elif ema[i - 1] is not None:
            ema.append((prices[i] - ema[i - 1]) * multiplier + ema[i - 1])
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
        sma = sum(prices[i - period + 1 : i + 1]) / period
        std = math.sqrt(sum((p - sma) ** 2 for p in prices[i - period + 1 : i + 1]) / period)
        bands.append({
            "middle": round(sma, 2),
            "upper": round(sma + 2 * std, 2),
            "lower": round(sma - 2 * std, 2),
        })
    return bands


def run_engine(symbol: str) -> dict:
    seed = hash(symbol) % (2**31)
    rng = random.Random(seed)

    base_price_map = {"600519": 1850, "000300": 4200, "TL": 105.5, "default": 100}
    base_price = base_price_map.get(symbol, base_price_map["default"])

    klines = generate_kline(base_price, 120, seed)
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
    ma_alignment = "多头排列" if last_ma5 > last_ma10 > last_ma20 > last_ma60 else "空头排列" if last_ma5 < last_ma10 < last_ma20 < last_ma60 else "交叉缠绕"

    return {
        "symbol": symbol,
        "symbol_name": {"600519": "贵州茅台", "000300": "沪深300", "TL": "TL主力合约"}.get(symbol, symbol),
        "data_points": len(klines),
        "latest": {
            "price": latest["close"],
            "change": round((latest["close"] - klines[-2]["close"]) / klines[-2]["close"] * 100, 2) if len(klines) > 1 else 0,
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
            "position": "上轨附近" if latest["close"] >= (last_boll["upper"] or 0) * 0.98 else "下轨附近" if latest["close"] <= (last_boll["lower"] or 0) * 1.02 else "中轨附近",
        },
        "support_levels": [round(min(lows[-20:]), 2), round(min(lows[-10:]), 2)],
        "resistance_levels": [round(max(highs[-20:]), 2), round(max(highs[-10:]), 2)],
        "volume_trend": "放量" if latest["volume"] > sum(k["volume"] for k in klines[-5:]) / 5 * 1.2 else "缩量" if latest["volume"] < sum(k["volume"] for k in klines[-5:]) / 5 * 0.8 else "正常",
    }


if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "600519"
    result = run_engine(symbol)
    print(json.dumps(result, ensure_ascii=False, indent=2))
