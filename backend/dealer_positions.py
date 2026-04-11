"""Dealer Positions Engine — Reverse-engineer institutional positioning.

3 Systems:
1. DEALER PANIC VELOCITY — How fast are sellers covering? Speed = panic = explosive move
2. GAMMA SQUEEZE DETECTOR — Feedback loop: buyers push → dealers forced to buy more → price explodes
3. DEALER DELTA RECONSTRUCTION — Net dealer position: long or short delta? Flip = THE signal

Data: Uses option chain OI + volume + price + Greeks across cycles.
Persistence: Tracks history across cycles for velocity/acceleration calculations.
"""

import math
import time
from collections import deque
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

# ── Config ──
VELOCITY_WINDOW = 20       # last 20 cycles (~100 seconds at 5s refresh)
PANIC_THRESHOLD = 15000    # OI/min covering speed = panic
GAMMA_SQUEEZE_MIN = 0.6    # gamma concentration ratio for squeeze
DELTA_FLIP_MIN = 0.15      # minimum delta change to count as flip

# ── Persistence across cycles ──
_oi_history: dict[str, deque] = {}      # "strike_side" → deque of (timestamp, oi)
_price_history: dict[str, deque] = {}   # "strike_side" → deque of (timestamp, price)
_dealer_delta_history: deque = deque(maxlen=200)  # (timestamp, net_delta)
_last_cycle_ts: float = 0

# ── Black-Scholes helpers ──
_SQRT2PI = math.sqrt(2 * math.pi)

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

def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT2PI

def _bs_delta(S, K, T, r, sigma, is_call=True):
    if T <= 0 or sigma <= 0 or S <= 0: return 0.5 if is_call else -0.5
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    return _norm_cdf(d1) if is_call else _norm_cdf(d1) - 1

def _bs_gamma(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0 or S <= 0: return 0
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    return _norm_pdf(d1) / (S * sigma * math.sqrt(T))


def analyze(chain: dict, spot: float, atm: int, strike_step: int = 50,
            time_to_expiry_mins: float = 60, lot_size: int = 75) -> dict:
    """Full dealer position analysis. Called every cycle."""
    global _last_cycle_ts

    now = datetime.now(IST)
    now_ts = time.time()
    h, m = now.hour, now.minute
    r = 0.065  # risk-free rate
    T = max(time_to_expiry_mins / (365 * 24 * 60), 0.0001)

    if not chain or spot <= 0:
        return _empty(now)

    strikes = sorted(chain.keys())
    cycle_gap = now_ts - _last_cycle_ts if _last_cycle_ts > 0 else 5
    _last_cycle_ts = now_ts

    # ══════════════════════════════════════════
    #  1. RECORD OI + PRICE HISTORY
    # ══════════════════════════════════════════
    for strike in strikes:
        dist = abs(strike - atm) / strike_step
        if dist > 8: continue
        for side_key in ("CE", "PE"):
            info = chain[strike].get(side_key)
            if not info: continue
            key = f"{int(strike)}_{side_key}"
            if key not in _oi_history:
                _oi_history[key] = deque(maxlen=VELOCITY_WINDOW)
                _price_history[key] = deque(maxlen=VELOCITY_WINDOW)
            _oi_history[key].append((now_ts, info.get("oi", 0)))
            _price_history[key].append((now_ts, info.get("last_price", 0)))

    # ══════════════════════════════════════════
    #  2. DEALER PANIC VELOCITY
    # ══════════════════════════════════════════
    panic_events = []
    for key, hist in _oi_history.items():
        if len(hist) < 4: continue
        # Calculate OI velocity (OI change per minute)
        oldest_ts, oldest_oi = hist[0]
        newest_ts, newest_oi = hist[-1]
        time_diff_min = (newest_ts - oldest_ts) / 60
        if time_diff_min < 0.3: continue  # need at least 20 seconds

        oi_change = newest_oi - oldest_oi
        velocity = oi_change / time_diff_min  # OI per minute

        # Acceleration: is velocity increasing?
        if len(hist) >= 8:
            mid = len(hist) // 2
            first_half_vel = (hist[mid][1] - hist[0][1]) / max((hist[mid][0] - hist[0][0]) / 60, 0.1)
            second_half_vel = (hist[-1][1] - hist[mid][1]) / max((hist[-1][0] - hist[mid][0]) / 60, 0.1)
            acceleration = second_half_vel - first_half_vel
        else:
            acceleration = 0

        # Panic = OI dropping fast (negative velocity, large magnitude)
        if velocity < -PANIC_THRESHOLD:
            strike_num = int(key.split("_")[0])
            side = key.split("_")[1]

            # Get price change during this period
            p_hist = _price_history.get(key, [])
            price_change = 0
            if len(p_hist) >= 2:
                price_change = p_hist[-1][1] - p_hist[0][1]

            panic_events.append({
                "strike": strike_num,
                "side": side,
                "velocity": round(velocity, 0),
                "acceleration": round(acceleration, 0),
                "oi_change": oi_change,
                "price_change": round(price_change, 2),
                "time_span_sec": round(time_diff_min * 60, 0),
                "level": "EXTREME" if velocity < -PANIC_THRESHOLD * 3 else "HIGH" if velocity < -PANIC_THRESHOLD * 2 else "PANIC",
                "detail": f"{side} sellers at {strike_num} covering at {abs(velocity):,.0f} OI/min — {'ACCELERATING' if acceleration < -5000 else 'steady'} — price {'rising' if price_change > 0 else 'falling'} ₹{abs(price_change):.1f}",
                "buyer_action": f"BUY {'CE' if side == 'CE' and price_change > 0 else 'PE' if side == 'PE' and price_change > 0 else 'WATCH'}",
            })

    panic_events.sort(key=lambda x: x["velocity"])  # most negative first

    # Overall panic level
    if any(p["level"] == "EXTREME" for p in panic_events):
        panic_level = "EXTREME"
        panic_msg = "DEALER PANIC — multiple strikes unwinding at extreme speed. EXPLOSIVE MOVE imminent."
    elif len(panic_events) >= 3:
        panic_level = "HIGH"
        panic_msg = f"Dealers covering fast at {len(panic_events)} strikes. Big move building."
    elif len(panic_events) >= 1:
        panic_level = "ELEVATED"
        panic_msg = f"Dealer covering detected at {len(panic_events)} strike(s). Watch closely."
    else:
        panic_level = "NORMAL"
        panic_msg = "No dealer panic. Normal OI flow."

    # ══════════════════════════════════════════
    #  3. GAMMA SQUEEZE DETECTOR
    # ══════════════════════════════════════════
    ce_gamma_total = 0
    pe_gamma_total = 0
    gamma_per_strike = []
    max_gamma_strike = None
    max_gamma_val = 0

    for strike in strikes:
        dist = abs(strike - atm) / strike_step
        if dist > 5: continue

        for side_key in ("CE", "PE"):
            info = chain[strike].get(side_key)
            if not info or info.get("iv", 0) <= 0: continue

            sigma = info["iv"] / 100
            oi = info.get("oi", 0)
            gamma = _bs_gamma(spot, float(strike), T, r, sigma)
            gex = gamma * oi * lot_size

            if side_key == "CE":
                ce_gamma_total += gex
            else:
                pe_gamma_total += gex

            gamma_per_strike.append({
                "strike": int(strike),
                "side": side_key,
                "gamma": round(gamma, 8),
                "gex": round(gex, 0),
                "oi": oi,
            })

            if abs(gex) > max_gamma_val:
                max_gamma_val = abs(gex)
                max_gamma_strike = {"strike": int(strike), "side": side_key, "gex": round(gex, 0)}

    net_gex = ce_gamma_total - pe_gamma_total
    total_gex = ce_gamma_total + pe_gamma_total

    # Gamma concentration: is gamma concentrated at few strikes? = squeeze potential
    gamma_vals = sorted([abs(g["gex"]) for g in gamma_per_strike], reverse=True)
    top3_gamma = sum(gamma_vals[:3]) if len(gamma_vals) >= 3 else sum(gamma_vals)
    gamma_concentration = top3_gamma / total_gex if total_gex > 0 else 0

    # Squeeze detection
    squeeze_active = False
    squeeze_direction = "NEUTRAL"
    squeeze_detail = ""

    if gamma_concentration > GAMMA_SQUEEZE_MIN:
        squeeze_active = True
        if net_gex < 0:
            squeeze_direction = "BULLISH"
            squeeze_detail = f"Negative GEX ({net_gex:,.0f}) + high gamma concentration ({gamma_concentration:.0%}) at {max_gamma_strike['strike'] if max_gamma_strike else 'ATM'}. Dealers SHORT gamma — forced to BUY on up-move. FEEDBACK LOOP = explosive up move."
        else:
            squeeze_direction = "BEARISH"
            squeeze_detail = f"Positive GEX ({net_gex:,.0f}) + high concentration. Dealers LONG gamma — will sell on up-move, buy on down-move. Market likely to PIN near {atm}."

    # ══════════════════════════════════════════
    #  4. DEALER DELTA RECONSTRUCTION
    # ══════════════════════════════════════════
    # Dealer is SHORT options (they sell to buyers). Their delta = negative of buyer's delta.
    # If buyer bought calls → dealer is short calls → dealer is SHORT delta → dealer must BUY futures to hedge
    # If buyer bought puts → dealer is short puts → dealer is LONG delta → dealer must SELL futures to hedge

    net_dealer_delta = 0
    delta_breakdown = []

    for strike in strikes:
        dist = abs(strike - atm) / strike_step
        if dist > 6: continue

        for side_key in ("CE", "PE"):
            info = chain[strike].get(side_key)
            if not info or info.get("iv", 0) <= 0: continue

            sigma = info["iv"] / 100
            oi = info.get("oi", 0)
            is_call = side_key == "CE"
            delta = _bs_delta(spot, float(strike), T, r, sigma, is_call)

            # Dealer is SHORT these options, so dealer's delta = -1 × (buyer's delta × OI × lot)
            dealer_delta = -1 * delta * oi * lot_size
            net_dealer_delta += dealer_delta

            if abs(oi) > 10000:  # only significant positions
                delta_breakdown.append({
                    "strike": int(strike),
                    "side": side_key,
                    "delta": round(delta, 4),
                    "oi": oi,
                    "dealer_delta": round(dealer_delta, 0),
                    "direction": "LONG" if dealer_delta > 0 else "SHORT",
                })

    delta_breakdown.sort(key=lambda x: abs(x["dealer_delta"]), reverse=True)

    # Track delta over time for flip detection
    _dealer_delta_history.append((now_ts, net_dealer_delta))

    # Delta flip detection
    delta_flip = False
    flip_direction = "NONE"
    flip_detail = ""

    if len(_dealer_delta_history) >= 10:
        recent = list(_dealer_delta_history)
        old_delta = sum(d[1] for d in recent[-10:-5]) / 5
        new_delta = sum(d[1] for d in recent[-5:]) / 5

        if old_delta != 0:
            change_pct = (new_delta - old_delta) / abs(old_delta)
            if abs(change_pct) > DELTA_FLIP_MIN:
                if old_delta > 0 and new_delta < 0:
                    delta_flip = True
                    flip_direction = "BEARISH FLIP"
                    flip_detail = f"Dealers flipped from LONG delta ({old_delta:,.0f}) to SHORT delta ({new_delta:,.0f}). They were buying futures, now SELLING. Market will DROP."
                elif old_delta < 0 and new_delta > 0:
                    delta_flip = True
                    flip_direction = "BULLISH FLIP"
                    flip_detail = f"Dealers flipped from SHORT delta ({old_delta:,.0f}) to LONG delta ({new_delta:,.0f}). They were selling futures, now BUYING. Market will RISE."

    # Dealer stance
    if net_dealer_delta > 0:
        dealer_stance = "LONG DELTA — Dealers buying futures to hedge. Supportive for market."
        stance_color = "green"
    elif net_dealer_delta < 0:
        dealer_stance = "SHORT DELTA — Dealers selling futures to hedge. Pressure on market."
        stance_color = "red"
    else:
        dealer_stance = "NEUTRAL — Dealers delta-neutral."
        stance_color = "gray"

    # ══════════════════════════════════════════
    #  5. BUYER SIGNALS from dealer analysis
    # ══════════════════════════════════════════
    signals = []

    # Panic covering = BUY
    for p in panic_events[:2]:
        if p["price_change"] > 0 and p["side"] == "CE":
            signals.append({"signal": "BUY CE", "source": "DEALER PANIC",
                            "reason": p["detail"], "conviction": p["level"]})
        elif p["price_change"] > 0 and p["side"] == "PE":
            signals.append({"signal": "BUY PE", "source": "DEALER PANIC",
                            "reason": p["detail"], "conviction": p["level"]})

    # Gamma squeeze = BUY in squeeze direction
    if squeeze_active:
        sig = "BUY CE" if squeeze_direction == "BULLISH" else "AVOID — market pinning"
        signals.append({"signal": sig, "source": "GAMMA SQUEEZE",
                        "reason": squeeze_detail, "conviction": "HIGH" if squeeze_direction == "BULLISH" else "WARNING"})

    # Delta flip = strongest signal
    if delta_flip:
        sig = "BUY CE" if flip_direction == "BULLISH FLIP" else "BUY PE"
        signals.append({"signal": sig, "source": "DEALER DELTA FLIP",
                        "reason": flip_detail, "conviction": "MAXIMUM"})

    return {
        "timestamp": now.isoformat(),
        "spot": round(spot, 2),
        "atm": atm,

        # 1. Panic Velocity
        "panic_level": panic_level,
        "panic_msg": panic_msg,
        "panic_events": panic_events[:5],

        # 2. Gamma Squeeze
        "squeeze_active": squeeze_active,
        "squeeze_direction": squeeze_direction,
        "squeeze_detail": squeeze_detail,
        "net_gex": round(net_gex, 0),
        "ce_gex": round(ce_gamma_total, 0),
        "pe_gex": round(pe_gamma_total, 0),
        "gamma_concentration": round(gamma_concentration, 2),
        "max_gamma_strike": max_gamma_strike,

        # 3. Dealer Delta
        "net_dealer_delta": round(net_dealer_delta, 0),
        "dealer_stance": dealer_stance,
        "stance_color": stance_color,
        "delta_flip": delta_flip,
        "flip_direction": flip_direction,
        "flip_detail": flip_detail,
        "delta_breakdown": delta_breakdown[:8],
        "delta_history": [{"ts": d[0], "delta": round(d[1], 0)} for d in list(_dealer_delta_history)[-30:]],

        # Combined signals
        "signals": signals,
    }


def _empty(now) -> dict:
    return {
        "timestamp": now.isoformat(), "spot": 0, "atm": 0,
        "panic_level": "NORMAL", "panic_msg": "No data", "panic_events": [],
        "squeeze_active": False, "squeeze_direction": "NEUTRAL", "squeeze_detail": "",
        "net_gex": 0, "ce_gex": 0, "pe_gex": 0, "gamma_concentration": 0, "max_gamma_strike": None,
        "net_dealer_delta": 0, "dealer_stance": "No data", "stance_color": "gray",
        "delta_flip": False, "flip_direction": "NONE", "flip_detail": "",
        "delta_breakdown": [], "delta_history": [], "signals": [],
    }
