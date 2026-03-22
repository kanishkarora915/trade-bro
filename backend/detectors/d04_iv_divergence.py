"""Detector 4 — IV Divergence. Finds strikes where IV deviates from the vol smile curve."""
import numpy as np


def detect(data: dict) -> dict:
    chain = data.get("chain", {})
    atm = data.get("atm", 24300)
    alerts = []
    top_score = 0

    for side_key in ("CE", "PE"):
        strikes = []
        ivs = []
        for strike, sides in sorted(chain.items()):
            info = sides.get(side_key)
            if info and info.get("iv", 0) > 0:
                strikes.append(strike)
                ivs.append(info["iv"])

        if len(strikes) < 5:
            continue

        x = np.array(strikes)
        y = np.array(ivs)
        try:
            coeffs = np.polyfit(x - atm, y, 2)
            expected = np.polyval(coeffs, x - atm)
        except Exception:
            continue

        for i, strike in enumerate(strikes):
            dev = ivs[i] - expected[i]
            if abs(dev) > 1.5:
                sc = min(100, abs(dev) / 5 * 100)
                top_score = max(top_score, sc)
                direction = f"Hidden {'CALL' if side_key == 'CE' else 'PUT'} demand" if dev > 0 else "IV suppressed"
                status = "CRITICAL" if abs(dev) > 3.5 else "ALERT" if abs(dev) > 2.5 else "WATCH"
                alerts.append({
                    "strike": f"{int(strike)} {side_key}",
                    "expected_iv": f"{expected[i]:.1f}%",
                    "actual_iv": f"{ivs[i]:.1f}%",
                    "deviation": f"{dev:+.1f}%",
                    "direction": direction,
                    "status": status,
                    "score": round(sc, 1),
                })

    alerts.sort(key=lambda a: a["score"], reverse=True)
    best = alerts[0] if alerts else None

    return {
        "id": "d04_iv_divergence",
        "name": "IV Divergence",
        "score": round(top_score, 1),
        "status": best["status"] if best else "NORMAL",
        "metric": f"{best['deviation']} dev" if best else "Normal",
        "alerts": alerts[:5],
    }
