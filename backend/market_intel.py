"""Market Intelligence — Regime Detection + Theta Calculator + Expiry Day Mode.

1. REGIME: Is today trending or range-bound? Range = buyer dies.
2. THETA: How much premium is decaying per minute for active position.
3. EXPIRY MODE: Different rules on expiry day (theta 10x, exit by 3:20).
"""

import math
from datetime import datetime, timezone, timedelta
from collections import deque

IST = timezone(timedelta(hours=5, minutes=30))

# ── Regime detection history ──
_spot_ticks: deque = deque(maxlen=300)  # ~25 min of 5-sec ticks


def _calc_regime(spot: float) -> dict:
    """Detect market regime: TRENDING UP / TRENDING DOWN / RANGE-BOUND / VOLATILE."""
    _spot_ticks.append((datetime.now(IST).timestamp(), spot))

    if len(_spot_ticks) < 20:
        return {"regime": "UNKNOWN", "detail": "Need more data", "color": "gray",
                "range_pts": 0, "trend_strength": 0, "buyer_advice": "Wait for regime to establish"}

    prices = [p[1] for p in _spot_ticks]
    recent_60 = prices[-12:]   # last 1 min
    recent_300 = prices[-60:]  # last 5 min
    all_prices = prices

    high = max(all_prices)
    low = min(all_prices)
    range_pts = high - low
    current = prices[-1]
    start = prices[0]
    net_move = current - start

    # 5-min trend
    high_5m = max(recent_300)
    low_5m = min(recent_300)
    range_5m = high_5m - low_5m

    # Higher highs / higher lows detection
    chunks = [prices[i:i+12] for i in range(0, len(prices)-11, 12)]
    if len(chunks) >= 3:
        chunk_highs = [max(c) for c in chunks]
        chunk_lows = [min(c) for c in chunks]
        hh = all(chunk_highs[i] > chunk_highs[i-1] for i in range(1, len(chunk_highs)))
        hl = all(chunk_lows[i] > chunk_lows[i-1] for i in range(1, len(chunk_lows)))
        lh = all(chunk_highs[i] < chunk_highs[i-1] for i in range(1, len(chunk_highs)))
        ll = all(chunk_lows[i] < chunk_lows[i-1] for i in range(1, len(chunk_lows)))
    else:
        hh = hl = lh = ll = False

    # Trend strength (0-100)
    if range_pts > 0:
        trend_strength = abs(net_move) / range_pts * 100
    else:
        trend_strength = 0

    # Classify
    if hh and hl and trend_strength > 60:
        regime = "TRENDING UP"
        color = "green"
        detail = f"Higher highs + higher lows. Net move +{net_move:.1f} pts. Range {range_pts:.0f} pts."
        advice = "BUY CE — trend is your friend. Trail SL, don't exit early."
    elif lh and ll and trend_strength > 60:
        regime = "TRENDING DOWN"
        color = "red"
        detail = f"Lower highs + lower lows. Net move {net_move:.1f} pts. Range {range_pts:.0f} pts."
        advice = "BUY PE — downtrend confirmed. Trail SL, let it run."
    elif range_5m < spot * 0.002:  # less than 0.2% range in 5 min
        regime = "RANGE-BOUND"
        color = "yellow"
        detail = f"Tight range {range_5m:.0f} pts in 5 min. No clear direction."
        advice = "AVOID BUYING — premium will decay in range. Wait for breakout."
    elif range_pts > spot * 0.008:  # more than 0.8% total range
        regime = "VOLATILE"
        color = "orange"
        detail = f"High volatility — {range_pts:.0f} pts range. Wild swings."
        advice = "CAUTION — wide SL needed. Reduce lot size. Quick scalps only."
    else:
        regime = "CONSOLIDATING"
        color = "blue"
        detail = f"Sideways with {range_pts:.0f} pts range. Building energy."
        advice = "WATCHLIST — consolidation often precedes breakout. Wait for direction."

    return {
        "regime": regime,
        "detail": detail,
        "color": color,
        "range_pts": round(range_pts, 1),
        "range_5m": round(range_5m, 1),
        "net_move": round(net_move, 1),
        "trend_strength": round(trend_strength, 1),
        "buyer_advice": advice,
        "data_points": len(prices),
    }


def _calc_theta(ltp: float, strike: float, spot: float, iv: float,
                time_to_expiry_mins: float, is_call: bool, lot_size: int, lots: int) -> dict:
    """Calculate theta decay for buyer's position."""
    if iv <= 0 or ltp <= 0 or time_to_expiry_mins <= 0:
        return {"theta_per_min": 0, "theta_per_lot_min": 0, "burn_30min": 0, "warning": ""}

    sigma = iv / 100
    T = time_to_expiry_mins / (365 * 24 * 60)
    r = 0.065

    if T <= 0 or sigma <= 0:
        return {"theta_per_min": 0, "theta_per_lot_min": 0, "burn_30min": 0, "warning": ""}

    # Black-Scholes Theta
    d1 = (math.log(spot / strike) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    nd1 = math.exp(-0.5 * d1**2) / math.sqrt(2 * math.pi)

    # Theta in ₹ per day
    theta_day = -(spot * nd1 * sigma) / (2 * math.sqrt(T))
    if is_call:
        theta_day -= r * strike * math.exp(-r * T) * _norm_cdf(d2)
    else:
        theta_day += r * strike * math.exp(-r * T) * _norm_cdf(-d2)

    # Convert to per minute (trading day = 375 minutes)
    theta_per_min = theta_day / 375
    theta_per_lot_min = theta_per_min * lot_size * lots
    burn_30min = abs(theta_per_lot_min * 30)

    # Warning levels
    if abs(theta_per_lot_min) > ltp * lot_size * lots * 0.01:  # >1% per minute
        warning = "EXTREME THETA — premium melting fast. Exit if no movement in 10 min."
    elif abs(theta_per_lot_min) > ltp * lot_size * lots * 0.003:  # >0.3% per minute
        warning = "High theta decay. 30 min max hold without movement."
    else:
        warning = ""

    return {
        "theta_per_min": round(abs(theta_per_min), 2),
        "theta_per_lot_min": round(abs(theta_per_lot_min), 2),
        "burn_30min": round(burn_30min, 0),
        "burn_60min": round(abs(theta_per_lot_min * 60), 0),
        "theta_day_total": round(abs(theta_day * lot_size * lots), 0),
        "warning": warning,
    }


def _norm_cdf(x: float) -> float:
    if x < -6: return 0.0
    if x > 6: return 1.0
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p = 0.3275911
    sign = 1 if x >= 0 else -1
    x = abs(x)
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x / 2)
    return 0.5 * (1.0 + sign * y)


def _check_expiry_mode(time_to_expiry_mins: float) -> dict:
    """Check if expiry day and return special rules."""
    now = datetime.now(IST)
    h, m = now.hour, now.minute

    is_expiry = time_to_expiry_mins < 24 * 60  # less than 1 day = expiry day

    if not is_expiry:
        return {"is_expiry": False, "mode": "NORMAL", "rules": [], "color": "gray"}

    rules = [
        "Theta 10x faster — every minute counts",
        "Max hold: 20 minutes without target",
        "SL tighter: 10% instead of 15%",
        "Exit ALL positions by 3:20 PM",
        "Avoid entry after 2:45 PM",
        "Only ATM strikes — OTM will go to zero",
    ]

    if h >= 14 and m >= 45:
        mode = "DANGER ZONE"
        color = "red"
        rules.insert(0, "DANGER ZONE — after 2:45 PM on expiry. EXIT or don't enter.")
    elif h >= 14:
        mode = "LATE EXPIRY"
        color = "orange"
        rules.insert(0, "Late expiry — tighten all SLs, quick exits only.")
    else:
        mode = "EXPIRY DAY"
        color = "yellow"

    return {
        "is_expiry": True,
        "mode": mode,
        "color": color,
        "rules": rules,
        "time_to_expiry_mins": round(time_to_expiry_mins, 0),
        "hours_left": round(time_to_expiry_mins / 60, 1),
    }


def analyze(spot: float, chain: dict, atm: int, time_to_expiry_mins: float,
            active_trade: dict | None = None, lot_size: int = 75) -> dict:
    """Full market intelligence analysis."""
    now = datetime.now(IST)

    # 1. Regime
    regime = _calc_regime(spot)

    # 2. Theta (if active trade)
    theta = {"theta_per_min": 0, "theta_per_lot_min": 0, "burn_30min": 0, "warning": ""}
    if active_trade and chain:
        strike_num = int(active_trade.get("strike", "0").split()[0])
        side = active_trade.get("side", "CE")
        info = chain.get(strike_num, {}).get(side, {})
        if info:
            theta = _calc_theta(
                ltp=info.get("last_price", 0),
                strike=strike_num,
                spot=spot,
                iv=info.get("iv", 15),
                time_to_expiry_mins=time_to_expiry_mins,
                is_call=(side == "CE"),
                lot_size=lot_size,
                lots=active_trade.get("lots", 1),
            )

    # 3. Expiry mode
    expiry = _check_expiry_mode(time_to_expiry_mins)

    # 4. Trade-ability score (should buyer trade today?)
    tradeability = 100
    reasons_no = []

    if regime["regime"] == "RANGE-BOUND":
        tradeability -= 40
        reasons_no.append("Range-bound market — premium will decay")
    if regime["regime"] == "VOLATILE":
        tradeability -= 20
        reasons_no.append("High volatility — wide SL needed")
    if expiry["is_expiry"] and time_to_expiry_mins < 120:
        tradeability -= 30
        reasons_no.append("Expiry day late session — theta extreme")
    if theta.get("warning"):
        tradeability -= 15
        reasons_no.append(theta["warning"][:50])

    tradeability = max(0, min(100, tradeability))
    trade_verdict = "GO" if tradeability >= 60 else "CAUTION" if tradeability >= 30 else "AVOID"

    return {
        "timestamp": now.isoformat(),
        "regime": regime,
        "theta": theta,
        "expiry": expiry,
        "tradeability": {
            "score": tradeability,
            "verdict": trade_verdict,
            "reasons_against": reasons_no,
        },
    }
