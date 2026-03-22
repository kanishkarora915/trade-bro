"""Brain Signal Generator — converts confluence score into actionable trade recommendation."""
from datetime import datetime


def generate(confluence: dict, detector_results: dict, data: dict) -> dict:
    score = confluence.get("score", 0)
    direction = confluence.get("direction", "NEUTRAL")
    chain = data.get("chain", {})
    spot = data.get("spot", 24300)
    atm = data.get("atm", 24300)

    if score < 51 or direction == "NEUTRAL":
        return {
            "active": False,
            "message": "No trade — score below threshold",
            "score": score,
            "direction": direction,
            "primary": None,
            "secondary": None,
            "exit_rules": [],
        }

    # Find the hottest strike
    side = "CE" if direction == "BULLISH" else "PE"
    best_strike = None
    best_heat = 0

    for strike, sides in chain.items():
        info = sides.get(side, {})
        if not info:
            continue
        vol = info.get("volume", 0)
        avg = info.get("avg_5d_volume", 1) or 1
        heat = (vol / avg) * info.get("buy_pct", 0.5) * 2
        if heat > best_heat:
            best_heat = heat
            best_strike = strike

    if not best_strike:
        best_strike = atm + (100 if side == "CE" else -100)

    primary_info = chain.get(best_strike, {}).get(side, {})
    cmp = primary_info.get("last_price", 50)

    # Primary trade
    t1 = round(cmp * 1.40, 2)
    t2 = round(cmp * 1.80, 2)
    sl = round(cmp * 0.72, 2)

    # Secondary trade (more OTM)
    sec_strike = best_strike + (50 if side == "CE" else -50)
    sec_info = chain.get(sec_strike, {}).get(side, {})
    sec_cmp = sec_info.get("last_price", cmp * 0.5) if sec_info else cmp * 0.5
    sec_target = round(sec_cmp * 2.32, 2)
    sec_sl = round(sec_cmp * 0.65, 2)

    # Signal strength
    if score >= 86:
        strength = "EXTREME"
    elif score >= 76:
        strength = "STRONG"
    elif score >= 66:
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
        "timestamp": datetime.now().isoformat(),
    }
