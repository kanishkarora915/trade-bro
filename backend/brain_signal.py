"""Brain Signal Generator v3 — stable signals with cooldown + OTM section + accuracy tracking."""
from datetime import datetime, timezone, timedelta
import time as _time

IST = timezone(timedelta(hours=5, minutes=30))

# Signal persistence — prevent flip-flop
_last_signal_time: float = 0.0
_last_signal_direction: str = ""
_last_signal_strike: str = ""
SIGNAL_COOLDOWN_SEC = 300  # FIX #7: 5 min cooldown (was 10 min — too long)
HARD_FLIP_SCORE = 80       # FIX #7: score 80+ can override cooldown for opposite direction


def generate(confluence: dict, detector_results: dict, data: dict) -> dict:
    score = confluence.get("score", 0)
    direction = confluence.get("direction", "NEUTRAL")
    chain = data.get("chain", {})
    spot = data.get("spot", 24300)
    atm = data.get("atm", 24300)
    step = data.get("strike_step", 50) or 50

    # Count detector statuses
    critical_count = sum(1 for d in detector_results.values() if d.get("status") == "CRITICAL")
    alert_count = sum(1 for d in detector_results.values() if d.get("status") in ("CRITICAL", "ALERT"))
    watch_count = sum(1 for d in detector_results.values() if d.get("status") in ("CRITICAL", "ALERT", "WATCH"))

    # STABLE THRESHOLD — quality over quantity, fewer but better signals
    threshold = 55  # higher base = only strong signals pass
    if critical_count >= 4:
        threshold = 40  # very strong = lower bar
    elif critical_count >= 3:
        threshold = 45
    elif alert_count >= 4:
        threshold = 50

    # Time filter: block outside market hours entirely
    now = datetime.now(IST)
    h, m = now.hour, now.minute
    market_active = (h == 9 and m >= 18) or (10 <= h <= 14) or (h == 15 and m < 20)
    if not market_active:
        return {
            "active": False, "message": "Market closed — no signals outside 9:18-15:20 IST",
            "score": score, "direction": direction, "primary": None, "secondary": None,
            "otm_trades": [], "exit_rules": [], "firing": confluence.get("firing", []),
        }

    side = "CE" if direction == "BULLISH" else "PE"
    if direction == "NEUTRAL":
        side = "CE"  # default to CE for scanning

    # Collect ALL candidates — ATM and OTM only (skip ITM completely)
    atm_candidates = []
    otm_candidates = []

    for strike, sides in chain.items():
        info = sides.get(side, {})
        if not info or info.get("last_price", 0) <= 0:
            continue

        ltp = info.get("last_price", 0)
        vol = info.get("volume", 0)
        oi = info.get("oi", 0)
        oi_chg = info.get("oi_day_change", 0)
        bp = info.get("buy_pct", 0.5)

        # Proper ITM/OTM classification based on moneyness
        # CE: ITM if strike < spot, OTM if strike > spot
        # PE: ITM if strike > spot, OTM if strike < spot
        is_itm = (side == "CE" and strike < spot) or (side == "PE" and strike > spot)

        # Skip ITM options entirely — we only want ATM and OTM signals
        if is_itm and abs(strike - atm) > step:
            continue

        # Skip deep ITM (premium > 4% of spot)
        if ltp > spot * 0.04:
            continue

        # Composite score
        vol_score = min(100, (vol / 30000) * 100) if vol > 0 else 0
        oi_score = min(100, (oi_chg / 50000) * 100) if oi_chg > 0 else 0
        bp_score = bp * 100
        atm_dist = abs(strike - atm) / step
        proximity_score = max(0, 100 - atm_dist * 15)

        # FIX #12: Volume most reliable, OI least reliable
        heat = vol_score * 0.40 + proximity_score * 0.30 + oi_score * 0.15 + bp_score * 0.15
        entry = (strike, heat, ltp, info)

        # Classify: ATM (±1 strike from ATM) vs OTM (further OTM)
        is_otm = (side == "CE" and strike > atm) or (side == "PE" and strike < atm)
        if atm_dist <= 1:
            atm_candidates.append(entry)
        elif is_otm and ltp >= 2:  # True OTM only, not worthless
            otm_candidates.append(entry)

    atm_candidates.sort(key=lambda x: x[1], reverse=True)
    otm_candidates.sort(key=lambda x: x[1], reverse=True)

    # Build OTM trades ALWAYS (even below threshold) — these are independent opportunities
    otm_trades = []
    for strike, heat, ltp, info in otm_candidates[:3]:
        otm_t1 = round(ltp * 1.50, 2)
        otm_t2 = round(ltp * 2.50, 2)
        otm_sl = round(ltp * 0.60, 2)
        otm_trades.append({
            "strike": f"{int(strike)} {side}",
            "cmp": round(ltp, 1),
            "target1": round(otm_t1, 1),
            "target2": round(otm_t2, 1),
            "stop_loss": round(otm_sl, 1),
            "heat": round(heat, 1),
            "vol": info.get("volume", 0),
            "oi_chg": info.get("oi_day_change", 0),
            "risk": "HIGH" if ltp < 20 else "MEDIUM",
        })

    if not atm_candidates and not otm_candidates:
        return {
            "active": False, "message": "No suitable strike found", "score": score,
            "direction": direction, "primary": None, "secondary": None,
            "otm_trades": otm_trades, "exit_rules": [], "firing": confluence.get("firing", []),
        }

    # Below threshold — return OTM trades but no primary signal
    if score < threshold or direction == "NEUTRAL":
        return {
            "active": False,
            "message": f"No trade — score {score:.0f}/{threshold} threshold, {alert_count} detectors firing",
            "score": score,
            "direction": direction,
            "primary": None,
            "secondary": None,
            "otm_trades": otm_trades,  # OTM always shows!
            "exit_rules": [],
            "firing": confluence.get("firing", []),
        }

    # COOLDOWN: If a signal was generated recently, don't flip direction
    global _last_signal_time, _last_signal_direction, _last_signal_strike
    now_ts = _time.time()
    elapsed = now_ts - _last_signal_time

    if _last_signal_time > 0 and elapsed < SIGNAL_COOLDOWN_SEC:
        # Signal already active — only allow SAME direction or significantly stronger opposite
        if direction != _last_signal_direction:
            # FIX #7: Allow hard flip at score 80+ (was threshold+20)
            if score < HARD_FLIP_SCORE:
                return {
                    "active": True,
                    "message": f"Holding previous {_last_signal_direction} signal — {int(SIGNAL_COOLDOWN_SEC - elapsed)}s cooldown remaining",
                    "score": score,
                    "direction": _last_signal_direction,
                    "primary": None,
                    "secondary": None,
                    "otm_trades": otm_trades,
                    "exit_rules": [],
                    "firing": confluence.get("firing", []),
                    "cooldown_remaining": int(SIGNAL_COOLDOWN_SEC - elapsed),
                }

    # PRIMARY: Best ATM candidate (or best OTM if no ATM)
    primary_list = atm_candidates if atm_candidates else otm_candidates
    best_strike, _, cmp, primary_info = primary_list[0]

    # Dynamic target/SL based on signal strength
    if score >= 80:
        t1_mult, t2_mult, sl_mult = 1.40, 1.80, 0.72
    elif score >= 60:
        t1_mult, t2_mult, sl_mult = 1.35, 1.70, 0.75
    elif score >= 40:
        t1_mult, t2_mult, sl_mult = 1.30, 1.60, 0.78
    else:
        t1_mult, t2_mult, sl_mult = 1.25, 1.50, 0.80

    t1 = round(cmp * t1_mult, 2)
    t2 = round(cmp * t2_mult, 2)
    sl = round(cmp * sl_mult, 2)

    # SECONDARY: Next ATM candidate
    secondary = None
    if len(primary_list) > 1:
        sec_strike, _, sec_cmp, _ = primary_list[1]
        secondary = {
            "action": "BUY",
            "strike": f"{int(sec_strike)} {side}",
            "cmp": f"₹{sec_cmp:.0f}",
            "target": f"₹{round(sec_cmp * t1_mult):.0f} (+{int((t1_mult-1)*100)}%)",
            "stop_loss": f"₹{round(sec_cmp * sl_mult):.0f} (-{int((1-sl_mult)*100)}%)",
        }

    # Signal strength
    if score >= 85 and critical_count >= 4:
        strength = "EXTREME"
    elif score >= 70 and critical_count >= 3:
        strength = "STRONG"
    elif score >= 50:
        strength = "MODERATE"
    else:
        strength = "MILD"

    # Exit rules
    is_expiry = data.get("is_expiry_day", False)
    exit_rules = [
        {"rule": "Target Hit", "detail": f"T1 → Sell 50%, hold for T2 → Exit full"},
        {"rule": "Stop Loss", "detail": f"Premium falls to ₹{sl:.0f} → Exit"},
        {"rule": "Time Stop", "detail": "30 min without target/SL → EXIT (theta decay)"},
        {"rule": "Signal Drop", "detail": "Score drops <40 → EXIT immediately"},
    ]
    if is_expiry:
        exit_rules.append({"rule": "Expiry", "detail": "Exit all by 3:20 PM. After 2:45 widen SL"})

    # Record signal for cooldown
    _last_signal_time = _time.time()
    _last_signal_direction = direction
    _last_signal_strike = f"{int(best_strike)} {side}"

    return {
        "active": True,
        "score": score,
        "strength": strength,
        "direction": direction,
        "primary": {
            "action": "BUY",
            "strike": f"{int(best_strike)} {side}",
            "cmp": f"₹{cmp:.0f}",
            "cmp_raw": cmp,
            "target1": f"₹{t1:.0f} (+{int((t1_mult-1)*100)}%)",
            "target2": f"₹{t2:.0f} (+{int((t2_mult-1)*100)}%)",
            "stop_loss": f"₹{sl:.0f} (-{int((1-sl_mult)*100)}%)",
            "time_limit": "Exit by 30 min if target not hit",
        },
        "secondary": secondary,
        "otm_trades": otm_trades,
        "exit_rules": exit_rules,
        "firing": confluence.get("firing", []),
        "nifty_spot": round(spot, 2),
        "expiry": data.get("expiry_date", ""),
        "timestamp": datetime.now(IST).isoformat(),
    }
