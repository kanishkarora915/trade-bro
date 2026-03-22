"""Detector 16 — Liquidity Vacuum Detector. Finds empty zones in order book."""


def detect(data: dict) -> dict:
    depth_map = data.get("depth_map", {})
    spot = data.get("spot", 24300)
    chain = data.get("chain", {})

    if not depth_map:
        return {
            "id": "d16_vacuum",
            "name": "Liquidity Vacuum",
            "score": 0,
            "status": "NORMAL",
            "metric": "No data",
            "alerts": [],
        }

    strikes = sorted(depth_map.keys())
    total_depths = [depth_map[s]["CE"] + depth_map[s]["PE"] for s in strikes]
    avg_depth = sum(total_depths) / len(total_depths) if total_depths else 1

    # Find vacuum zones (< 10% of avg depth)
    threshold = avg_depth * 0.1
    vacuums = []
    current_vacuum_start = None
    current_vacuum_strikes = []

    for i, s in enumerate(strikes):
        depth = total_depths[i]
        if depth < threshold:
            if current_vacuum_start is None:
                current_vacuum_start = s
            current_vacuum_strikes.append(s)
        else:
            if current_vacuum_start is not None and len(current_vacuum_strikes) >= 2:
                vacuums.append({
                    "start": current_vacuum_start,
                    "end": current_vacuum_strikes[-1],
                    "points": int(current_vacuum_strikes[-1] - current_vacuum_start),
                    "strikes": len(current_vacuum_strikes),
                })
            current_vacuum_start = None
            current_vacuum_strikes = []

    if current_vacuum_start and len(current_vacuum_strikes) >= 2:
        vacuums.append({
            "start": current_vacuum_start,
            "end": current_vacuum_strikes[-1],
            "points": int(current_vacuum_strikes[-1] - current_vacuum_start),
            "strikes": len(current_vacuum_strikes),
        })

    alerts = []
    top_score = 0

    for v in vacuums:
        dist_to_spot = min(abs(spot - v["start"]), abs(spot - v["end"]))
        at_boundary = dist_to_spot < 60

        sc = min(100, v["points"] / 100 * 60)
        if at_boundary:
            sc = min(100, sc + 30)

        top_score = max(top_score, sc)
        status = "CRITICAL" if at_boundary and v["points"] > 30 else "ALERT" if v["points"] > 30 else "WATCH"

        alerts.append({
            "zone": f"{int(v['start'])} — {int(v['end'])}",
            "points": f"{v['points']} pts empty",
            "at_boundary": at_boundary,
            "status_text": "AT VACUUM BOUNDARY" if at_boundary else "VACUUM ZONE",
            "signal": f"Rapid {v['points']}-pt move if breached" if at_boundary else "Monitor approach",
            "status": status,
            "score": round(sc, 1),
        })

    alerts.sort(key=lambda a: a["score"], reverse=True)
    best = alerts[0] if alerts else None

    return {
        "id": "d16_vacuum",
        "name": "Liquidity Vacuum",
        "score": round(top_score, 1),
        "status": best["status"] if best else "NORMAL",
        "metric": f"{best['points']}" if best else "No vacuum",
        "alerts": alerts[:3],
    }
