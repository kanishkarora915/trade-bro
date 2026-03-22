"""Detector 1 — Unusual Options Activity (UOA). Detects volume spikes 3x+ above 5-day average."""


def _status(spike: float) -> str:
    if spike >= 12:
        return "CRITICAL"
    if spike >= 7:
        return "ALERT"
    if spike >= 3:
        return "WATCH"
    return "NORMAL"


def _score(spike: float) -> float:
    if spike < 3:
        return 0
    if spike >= 12:
        return 100
    return min(100, (spike - 3) / 9 * 100)


def detect(data: dict) -> dict:
    chain = data.get("chain", {})
    alerts = []
    top_score = 0

    for strike, sides in chain.items():
        for side_key in ("CE", "PE"):
            info = sides.get(side_key)
            if not info:
                continue
            vol = info.get("volume", 0)
            avg = info.get("avg_5d_volume", 1) or 1
            spike = vol / avg
            if spike >= 3:
                sc = _score(spike)
                top_score = max(top_score, sc)
                alerts.append({
                    "strike": f"{int(strike)} {side_key}",
                    "volume": vol,
                    "avg_5d": avg,
                    "spike": round(spike, 1),
                    "spike_pct": f"{int(spike * 100)}%",
                    "status": _status(spike),
                    "score": round(sc, 1),
                })

    alerts.sort(key=lambda a: a["spike"], reverse=True)
    best = alerts[0] if alerts else None

    return {
        "id": "d01_uoa",
        "name": "Unusual Options Activity",
        "score": round(top_score, 1),
        "status": best["status"] if best else "NORMAL",
        "metric": f"{best['spike_pct']} spike" if best else "No spike",
        "alerts": alerts[:5],
    }
