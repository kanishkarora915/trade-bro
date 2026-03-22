"""Detector 9 — Put-Call Skew Shift. Detects when call IV rises faster than put IV."""


def detect(data: dict) -> dict:
    history = data.get("skew_history", [])
    chain = data.get("chain", {})
    atm = data.get("atm", 24300)

    atm_data = chain.get(atm, {})
    ce_iv = atm_data.get("CE", {}).get("iv", 0)
    pe_iv = atm_data.get("PE", {}).get("iv", 0)

    if not history or len(history) < 2:
        return {
            "id": "d09_skew_shift",
            "name": "Skew Shift",
            "score": 0,
            "status": "NORMAL",
            "metric": "Insufficient data",
            "alerts": [],
        }

    old = history[0]
    ce_change = ce_iv - old.get("ce_iv", ce_iv)
    pe_change = pe_iv - old.get("pe_iv", pe_iv)
    diff = ce_change - pe_change

    if diff > 1.5:
        status = "CRITICAL"
        direction = "BULLISH FLIP DETECTED"
        signal = "Smart money buying upside"
        sc = min(100, 60 + diff * 10)
    elif diff > 0.5:
        status = "WATCH"
        direction = "BULLISH SHIFT"
        signal = "Call demand rising"
        sc = min(100, 30 + diff * 20)
    elif diff < -1.5:
        status = "CRITICAL"
        direction = "BEARISH FLIP DETECTED"
        signal = "Smart money buying downside"
        sc = min(100, 60 + abs(diff) * 10)
    elif diff < -0.5:
        status = "WATCH"
        direction = "BEARISH SHIFT"
        signal = "Put demand rising"
        sc = min(100, 30 + abs(diff) * 20)
    else:
        status = "NORMAL"
        direction = "NEUTRAL"
        signal = "Normal skew"
        sc = 0

    return {
        "id": "d09_skew_shift",
        "name": "Skew Shift",
        "score": round(sc, 1),
        "status": status,
        "metric": direction,
        "alerts": [{
            "ce_iv": f"{ce_iv:.1f}%",
            "pe_iv": f"{pe_iv:.1f}%",
            "ce_change": f"{ce_change:+.1f}%",
            "pe_change": f"{pe_change:+.1f}%",
            "direction": direction,
            "signal": signal,
            "status": status,
        }] if sc > 0 else [],
    }
