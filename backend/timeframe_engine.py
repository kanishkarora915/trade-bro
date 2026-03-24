"""Multi-Timeframe Engine — fetches candles at 7 intervals, calculates S/R + trend.

Uses Kite Historical API for: 3m, 5m, 15m, 30m, 1h, day, week.
Calculates per timeframe:
- Support / Resistance (swing high/low + pivot points)
- Trend direction (EMA 9 vs 21 crossover)
- Volume profile
- Breakout / Reversal detection
"""

import time
import numpy as np
from datetime import datetime, timedelta
from kite_client import KiteClient

TIMEFRAMES = {
    "3m": {"interval": "3minute", "days": 2, "label": "3 Min", "refresh": 180},
    "5m": {"interval": "5minute", "days": 3, "label": "5 Min", "refresh": 300},
    "15m": {"interval": "15minute", "days": 5, "label": "15 Min", "refresh": 900},
    "30m": {"interval": "30minute", "days": 10, "label": "30 Min", "refresh": 1800},
    "1h": {"interval": "60minute", "days": 15, "label": "1 Hour", "refresh": 3600},
    "1d": {"interval": "day", "days": 90, "label": "Daily", "refresh": 3600},
    "1w": {"interval": "week", "days": 365, "label": "Weekly", "refresh": 7200},
}

# NIFTY 50 instrument token (used for historical candles)
INDEX_TOKENS = {
    "NIFTY": "256265",      # NSE:NIFTY 50
    "BANKNIFTY": "260105",  # NSE:NIFTY BANK
    "SENSEX": "265",        # BSE:SENSEX
}


def _ema(data: list[float], period: int) -> list[float]:
    """Calculate Exponential Moving Average."""
    if len(data) < period:
        return data[:]
    k = 2 / (period + 1)
    ema = [sum(data[:period]) / period]
    for price in data[period:]:
        ema.append(price * k + ema[-1] * (1 - k))
    return ema


def _find_swing_highs(highs: list[float], lows: list[float], lookback: int = 5) -> tuple[list[float], list[float]]:
    """Find swing high/low levels for support/resistance."""
    supports = []
    resistances = []
    for i in range(lookback, len(highs) - lookback):
        # Swing high — resistance
        if highs[i] == max(highs[i - lookback:i + lookback + 1]):
            resistances.append(highs[i])
        # Swing low — support
        if lows[i] == min(lows[i - lookback:i + lookback + 1]):
            supports.append(lows[i])
    return supports, resistances


def _pivot_levels(high: float, low: float, close: float) -> dict:
    """Calculate classic pivot points."""
    pp = (high + low + close) / 3
    return {
        "pivot": round(pp, 2),
        "r1": round(2 * pp - low, 2),
        "r2": round(pp + (high - low), 2),
        "s1": round(2 * pp - high, 2),
        "s2": round(pp - (high - low), 2),
    }


def _cluster_levels(levels: list[float], tolerance_pct: float = 0.3) -> list[dict]:
    """Cluster nearby levels and count touches."""
    if not levels:
        return []
    levels = sorted(levels)
    clusters = []
    current = [levels[0]]

    for lv in levels[1:]:
        if abs(lv - current[0]) / current[0] * 100 < tolerance_pct:
            current.append(lv)
        else:
            avg = sum(current) / len(current)
            clusters.append({"level": round(avg, 2), "touches": len(current), "strength": min(100, len(current) * 25)})
            current = [lv]

    if current:
        avg = sum(current) / len(current)
        clusters.append({"level": round(avg, 2), "touches": len(current), "strength": min(100, len(current) * 25)})

    return sorted(clusters, key=lambda x: -x["touches"])


def analyze_candles(candles: list[dict], tf_key: str) -> dict:
    """Analyze a set of candles for one timeframe.

    Returns: trend, supports, resistances, volume_avg, breakout, pivot_levels, etc.
    """
    if not candles or len(candles) < 5:
        return {"error": "Insufficient data", "trend": "UNKNOWN", "supports": [], "resistances": []}

    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    volumes = [c.get("volume", 0) for c in candles]
    opens = [c["open"] for c in candles]

    # Current price
    last = candles[-1]
    current_price = last["close"]

    # EMA 9 and 21 for trend
    ema9 = _ema(closes, 9)
    ema21 = _ema(closes, 21)

    trend = "SIDEWAYS"
    trend_strength = 0
    if len(ema9) >= 2 and len(ema21) >= 2:
        if ema9[-1] > ema21[-1]:
            trend = "BULLISH"
            trend_strength = min(100, abs(ema9[-1] - ema21[-1]) / current_price * 10000)
        elif ema9[-1] < ema21[-1]:
            trend = "BEARISH"
            trend_strength = min(100, abs(ema9[-1] - ema21[-1]) / current_price * 10000)

    # Swing highs/lows for S/R
    lookback = 3 if tf_key in ("3m", "5m") else 5
    raw_supports, raw_resistances = _find_swing_highs(highs, lows, lookback)

    # Cluster similar levels
    supports = _cluster_levels(raw_supports)[:5]
    resistances = _cluster_levels(raw_resistances)[:5]

    # Nearest support/resistance to current price
    nearest_support = 0
    nearest_resistance = 0
    for s in supports:
        if s["level"] < current_price and (nearest_support == 0 or s["level"] > nearest_support):
            nearest_support = s["level"]
    for r in resistances:
        if r["level"] > current_price and (nearest_resistance == 0 or r["level"] < nearest_resistance):
            nearest_resistance = r["level"]

    # Pivot levels from last candle
    pivots = _pivot_levels(max(highs[-5:]), min(lows[-5:]), closes[-1])

    # Volume analysis
    vol_avg = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes) if volumes else 0
    vol_current = volumes[-1] if volumes else 0
    vol_ratio = vol_current / vol_avg if vol_avg > 0 else 1

    # Breakout detection: price breaking above recent resistance or below support
    recent_high = max(highs[-10:]) if len(highs) >= 10 else max(highs)
    recent_low = min(lows[-10:]) if len(lows) >= 10 else min(lows)
    breakout = "NONE"
    if current_price >= recent_high and vol_ratio > 1.3:
        breakout = "BREAKOUT UP"
    elif current_price <= recent_low and vol_ratio > 1.3:
        breakout = "BREAKOUT DOWN"

    # Reversal detection: large candle in opposite direction of trend
    if len(candles) >= 3:
        last3 = candles[-3:]
        if trend == "BEARISH" and all(c["close"] > c["open"] for c in last3[-2:]):
            breakout = "REVERSAL UP"
        elif trend == "BULLISH" and all(c["close"] < c["open"] for c in last3[-2:]):
            breakout = "REVERSAL DOWN"

    # Price change
    prev_close = closes[-2] if len(closes) >= 2 else closes[-1]
    change = current_price - prev_close
    change_pct = (change / prev_close * 100) if prev_close > 0 else 0

    return {
        "timeframe": tf_key,
        "label": TIMEFRAMES[tf_key]["label"],
        "trend": trend,
        "trend_strength": round(trend_strength, 1),
        "current_price": round(current_price, 2),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "nearest_support": nearest_support,
        "nearest_resistance": nearest_resistance,
        "supports": supports[:3],
        "resistances": resistances[:3],
        "pivots": pivots,
        "volume_avg": round(vol_avg),
        "volume_current": vol_current,
        "volume_ratio": round(vol_ratio, 2),
        "breakout": breakout,
        "ema9": round(ema9[-1], 2) if ema9 else 0,
        "ema21": round(ema21[-1], 2) if ema21 else 0,
        "high": round(max(highs[-20:]) if len(highs) >= 20 else max(highs), 2),
        "low": round(min(lows[-20:]) if len(lows) >= 20 else min(lows), 2),
        "candle_count": len(candles),
        "last_updated": datetime.now().isoformat(),
    }


class TimeframeEngine:
    """Fetches and analyzes multiple timeframes."""

    def __init__(self, kite: KiteClient):
        self.kite = kite
        self._cache: dict[str, tuple[float, dict]] = {}  # key -> (timestamp, analysis)
        self._candle_cache: dict[str, tuple[float, list]] = {}  # key -> (timestamp, candles)

    async def fetch_timeframe(self, index: str, tf_key: str) -> dict:
        """Fetch and analyze one timeframe for an index."""
        cache_key = f"{index}_{tf_key}"
        now = time.time()
        refresh = TIMEFRAMES[tf_key]["refresh"]

        # Check cache
        if cache_key in self._cache:
            ts, data = self._cache[cache_key]
            if now - ts < refresh:
                return data

        token = INDEX_TOKENS.get(index, "256265")
        cfg = TIMEFRAMES[tf_key]

        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=cfg["days"])).strftime("%Y-%m-%d")

        try:
            candles = await self.kite.get_historical(token, cfg["interval"], from_date, to_date)
            if not candles:
                return {"timeframe": tf_key, "label": cfg["label"], "error": "No data", "trend": "UNKNOWN"}

            analysis = analyze_candles(candles, tf_key)
            self._cache[cache_key] = (now, analysis)
            self._candle_cache[cache_key] = (now, candles)
            return analysis

        except Exception as e:
            print(f"[TF] Error fetching {index} {tf_key}: {e}")
            # Return cached if available
            if cache_key in self._cache:
                return self._cache[cache_key][1]
            return {"timeframe": tf_key, "label": cfg["label"], "error": str(e)[:100], "trend": "UNKNOWN"}

    async def fetch_all(self, index: str, short_only: bool = False) -> dict[str, dict]:
        """Fetch all timeframes for an index.

        short_only=True: only fetch 3m, 5m, 15m (fast, every cycle)
        short_only=False: fetch all 7 timeframes (slower, less frequent)
        """
        targets = ["3m", "5m", "15m"] if short_only else list(TIMEFRAMES.keys())
        results = {}
        for tf in targets:
            results[tf] = await self.fetch_timeframe(index, tf)
        return results

    def get_cached(self, index: str) -> dict[str, dict]:
        """Return all cached timeframe data for an index (no API calls)."""
        results = {}
        for tf in TIMEFRAMES:
            key = f"{index}_{tf}"
            if key in self._cache:
                results[tf] = self._cache[key][1]
        return results

    def get_candles(self, index: str, tf_key: str) -> list[dict]:
        """Return cached candles for a timeframe."""
        key = f"{index}_{tf_key}"
        if key in self._candle_cache:
            return self._candle_cache[key][1]
        return []
