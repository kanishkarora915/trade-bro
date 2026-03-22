"""Detector 3 — Strike Ladder Sweep. Detects buying across 3+ consecutive strikes within 60s."""


def detect(data: dict) -> dict:
    sweep_events = data.get("sweep_events", [])
    if not sweep_events:
        return {
            "id": "d03_sweep",
            "name": "Strike Ladder Sweep",
            "score": 0,
            "status": "NORMAL",
            "metric": "No sweep",
            "alerts": [],
        }

    alerts = []
    top_score = 0

    for ev in sweep_events:
        n = len(ev.get("strikes", []))
        if n >= 4:
            status = "CRITICAL"
            sc = 85 + min(15, (n - 4) * 5)
        elif n >= 3:
            status = "WATCH"
            sc = 55 + (n - 3) * 15
        else:
            continue

        sc = min(100, sc)
        top_score = max(top_score, sc)

        strikes_str = " → ".join(f"{int(s)} {ev['side']}" for s in ev["strikes"])
        alerts.append({
            "side": ev["side"],
            "strikes": strikes_str,
            "num_strikes": n,
            "total_lots": ev.get("total_lots", 0),
            "start_time": ev.get("start_time", ""),
            "end_time": ev.get("end_time", ""),
            "status": status,
            "score": round(sc, 1),
        })

    alerts.sort(key=lambda a: a["score"], reverse=True)
    best = alerts[0] if alerts else None

    return {
        "id": "d03_sweep",
        "name": "Strike Ladder Sweep",
        "score": round(top_score, 1),
        "status": best["status"] if best else "NORMAL",
        "metric": f"{best['num_strikes']} strikes swept" if best else "No sweep",
        "alerts": alerts,
    }
