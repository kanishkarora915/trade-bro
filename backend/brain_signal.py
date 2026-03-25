"""Brain Signal Generator v2 — high-quality trade signals with multi-factor confirmation."""
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))


def generate(confluence: dict, detector_results: dict, data: dict) -> dict:
    score = confluence.get("score", 0)
    direction = confluence.get("direction", "NEUTRAL")
    chain = data.get("chain", {})
    spot = data.get("spot", 24300)
    atm = data.get("atm", 24300)

    # Count detector statuses for quality gating
    critical_count = sum(1 for d in detector_results.values() if d.get("status") == "CRITICAL")
    alert_count = sum(1 for d in detector_results.values() if d.get("status") in ("CRITICAL", "ALERT"))

    # QUALITY GATE: need minimum detectors firing
    # At least 3 detectors in CRITICAL/ALERT = something real is happening
    threshold = 50  # base threshold — higher than before for quality
    if critical_count >= 4:
        threshold = 30  # very strong signal
    elif critical_count >= 3:
        threshold = 35
    elif alert_count >= 4:
        threshold = 40

    # Time filter: no signals in first 5 min (9:15-9:20) or last 15 min (3:15-3:30)
    now = datetime.now(IST)
    h, m = now.hour, now.minute
    market_open = (h == 9 and m < 20)
    market_close = (h == 15 and m >= 15) or h >= 16
    if market_open or market_close:
        threshold = 100  # effectively no signal near open/close

    if score < threshold or direction == "NEUTRAL" or alert_count < 2:
        return {
            "active": False,
            "message": f"No trade — score {score:.0f}/{threshold} threshold, {alert_count} detectors firing",
            "score": score,
            "direction": direction,
            "primary": None,
            "secondary": None,
            "exit_rules": [],
            "firing": confluence.get("firing", []),
        }

    # Find the BEST strike — weighted by volume, OI change, buy_pct
    side = "CE" if direction == "BULLISH" else "PE"
    candidates = []

    for strike, sides in chain.items():
        info = sides.get(side, {})
        if not info or info.get("last_price", 0) <= 0:
            continue

        ltp = info.get("last_price", 0)
        vol = info.get("volume", 0)
        oi = info.get("oi", 0)
        oi_chg = info.get("oi_day_change", 0)
        bp = info.get("buy_pct", 0.5)

        # Skip deep ITM (premium too high, poor risk-reward)
        if ltp > spot * 0.03:  # more than 3% of spot = too expensive
            continue
        # Skip very cheap OTM (< ₹5 = too risky, wide spreads)
        if ltp < 5:
            continue

        # Composite score: volume strength + OI buildup + buyer dominance + proximity to ATM
        vol_score = min(100, (vol / 50000) * 100) if vol > 0 else 0
        oi_score = min(100, (oi_chg / 100000) * 100) if oi_chg > 0 else 0
        bp_score = bp * 100
        # Prefer strikes near ATM (±2 strikes)
        atm_dist = abs(strike - atm) / data.get("strike_step", 50) if data.get("strike_step") else abs(strike - atm) / 50
        proximity_score = max(0, 100 - atm_dist * 20)

        heat = vol_score * 0.3 + oi_score * 0.3 + bp_score * 0.2 + proximity_score * 0.2
        candidates.append((strike, heat, ltp, info))

    candidates.sort(key=lambda x: x[1], reverse=True)

    if not candidates:
        return {
            "active": False, "message": "No suitable strike found", "score": score,
            "direction": direction, "primary": None, "secondary": None,
            "exit_rules": [], "firing": confluence.get("firing", []),
        }

    best_strike, _, cmp, primary_info = candidates[0]

    # Dynamic target/SL based on signal strength
    if score >= 80:
        t1_mult, t2_mult, sl_mult = 1.35, 1.70, 0.75
    elif score >= 60:
        t1_mult, t2_mult, sl_mult = 1.25, 1.50, 0.78
    else:
        t1_mult, t2_mult, sl_mult = 1.20, 1.40, 0.80

    t1 = round(cmp * t1_mult, 2)
    t2 = round(cmp * t2_mult, 2)
    sl = round(cmp * sl_mult, 2)

    # Secondary trade (next strike OTM)
    step = 50 if "NIFTY" in str(data.get("name", "NIFTY")) else 100
    sec_strike = best_strike + (step if side == "CE" else -step)
    sec_info = chain.get(sec_strike, {}).get(side, {})
    sec_cmp = sec_info.get("last_price", cmp * 0.5) if sec_info else cmp * 0.5
    sec_target = round(sec_cmp * 1.80, 2)
    sec_sl = round(sec_cmp * 0.65, 2)

    # Signal strength
    if score >= 85 and critical_count >= 4:
        strength = "EXTREME"
    elif score >= 70 and critical_count >= 3:
        strength = "STRONG"
    elif score >= 55:
        strength = "MODERATE"
    else:
        strength = "MILD"

    # Exit rules
    is_expiry = data.get("is_expiry_day", False)
    now = datetime.now()
    exit_rules = [
        {"rule": "Target Hit", "detail": f"T1 (+40%) → Sell 50%, hold for T2 (+80%) → Exit full"},
        {"rule": "Stop Loss", "detail": f"Premium falls 28% (₹{sl}) → Auto exit"},
        {"rule": "Time Stop", "detail": "30 min without target/SL → EXIT (theta decay)"},
        {"rule": "Signal Collapse", "detail": "Score drops from 80+ to <60 → EXIT immediately"},
    ]
    if is_expiry:
        exit_rules.append({"rule": "Expiry Special", "detail": "After 2:45 PM widen SL to 40%. Exit all by 3:20 PM"})

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
            "target1": f"₹{t1:.0f} (+40%)",
            "target2": f"₹{t2:.0f} (+80%)",
            "stop_loss": f"₹{sl:.0f} (-28%)",
            "time_limit": "Exit by 30 min if target not hit",
        },
        "secondary": {
            "action": "BUY",
            "strike": f"{int(sec_strike)} {side} (OTM aggressive)",
            "cmp": f"₹{sec_cmp:.0f}",
            "target": f"₹{sec_target:.0f} (+132%)",
            "stop_loss": f"₹{sec_sl:.0f} (-35%)",
        },
        "exit_rules": exit_rules,
        "firing": confluence.get("firing", []),
        "nifty_spot": round(spot, 2),
        "expiry": data.get("expiry_date", ""),
        "timestamp": datetime.now(IST).isoformat(),
    }
