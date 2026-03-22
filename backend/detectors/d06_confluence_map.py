"""Detector 6 — Multi-Strike Confluence Map. Aggregates signals across strikes to determine direction."""


def detect(data: dict, detector_results: dict | None = None) -> dict:
    chain = data.get("chain", {})
    atm = data.get("atm", 24300)

    ce_signals = 0
    pe_signals = 0
    strike_map = []

    for strike, sides in sorted(chain.items()):
        ce = sides.get("CE", {})
        pe = sides.get("PE", {})

        ce_heat = 0
        pe_heat = 0

        # Volume spike contribution
        ce_avg = ce.get("avg_5d_volume", 1) or 1
        pe_avg = pe.get("avg_5d_volume", 1) or 1
        if ce.get("volume", 0) / ce_avg > 3:
            ce_heat += 2
        if pe.get("volume", 0) / pe_avg > 3:
            pe_heat += 2

        # Buy flow contribution
        if ce.get("buy_pct", 0.5) > 0.65:
            ce_heat += 2
        if (1 - pe.get("buy_pct", 0.5)) > 0.65:
            pe_heat += 2

        # IV contribution
        if ce.get("iv", 0) > 14:
            ce_heat += 1
        if pe.get("iv", 0) > 14:
            pe_heat += 1

        ce_signals += ce_heat
        pe_signals += pe_heat

        net = ce_heat - pe_heat
        label = "HOT" if abs(net) >= 4 else "loading" if abs(net) >= 2 else "mild" if abs(net) >= 1 else "neutral"

        strike_map.append({
            "strike": int(strike),
            "ce_heat": ce_heat,
            "pe_heat": pe_heat,
            "net": net,
            "label": label,
            "is_atm": abs(strike - atm) < 25,
        })

    direction = "BULLISH" if ce_signals > pe_signals else "BEARISH" if pe_signals > ce_signals else "NEUTRAL"
    diff = abs(ce_signals - pe_signals)
    sc = min(100, diff / max(1, ce_signals + pe_signals) * 200)

    if diff < 3:
        status = "NORMAL"
    elif diff < 8:
        status = "WATCH"
    else:
        status = "ALERT"

    return {
        "id": "d06_confluence_map",
        "name": "Confluence Map",
        "score": round(sc, 1),
        "status": status,
        "metric": f"{direction} — CE:{ce_signals} PE:{pe_signals}",
        "direction": direction,
        "ce_signals": ce_signals,
        "pe_signals": pe_signals,
        "strike_map": strike_map,
        "alerts": [],
    }
