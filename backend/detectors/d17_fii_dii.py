"""Detector 17 — FII vs DII Battle Tracker."""


def detect(data: dict) -> dict:
    fii_dii = data.get("fii_dii", {})
    fii_net = fii_dii.get("fii_net_cr", 0)
    dii_net = fii_dii.get("dii_net_cr", 0)
    spot = data.get("spot", 24300)
    trend = data.get("trend", 0)

    total_activity = abs(fii_net) + abs(dii_net)
    if total_activity < 500:
        return {
            "id": "d17_fii_dii",
            "name": "FII vs DII",
            "score": 0,
            "status": "NORMAL",
            "metric": "Low activity",
            "alerts": [],
        }

    # Determine battle dynamics
    if fii_net > 1000 and trend > 0:
        signal = "FII buying + market up = momentum CONFIRMED"
        status = "ALERT"
        sc = 70
        action = "Go long — confirmed"
    elif fii_net < -1000 and dii_net > 500:
        if abs(fii_net) > abs(dii_net) * 1.2:
            signal = "FII selling > DII buying — floor WEAKENING"
            status = "ALERT"
            sc = 65
            action = "Warning: If DII support reduces → DROP"
        else:
            signal = "FII selling = DII buying — EQUILIBRIUM"
            status = "WATCH"
            sc = 40
            action = "Watch for DII fatigue"
    elif fii_net < -2000:
        signal = "FII heavy selling — BEARISH pressure"
        status = "CRITICAL"
        sc = 80
        action = "PE side opportunity"
    elif fii_net > 2000:
        signal = "FII heavy buying — BULLISH momentum"
        status = "CRITICAL"
        sc = 80
        action = "CE side confirmed"
    else:
        signal = "Mixed signals"
        status = "WATCH"
        sc = 25
        action = "Monitor"

    dominant = "FII" if abs(fii_net) > abs(dii_net) else "DII"

    return {
        "id": "d17_fii_dii",
        "name": "FII vs DII",
        "score": round(sc, 1),
        "status": status,
        "metric": f"{dominant} dominant",
        "alerts": [{
            "fii_net": f"₹{fii_net:,.0f} Cr",
            "dii_net": f"₹{dii_net:,.0f} Cr",
            "dominant": dominant,
            "signal": signal,
            "action": action,
            "status": status,
        }],
    }
