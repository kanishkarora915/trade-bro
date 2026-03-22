"""Detector 5 — Time & Sales Velocity Engine. Tracks contracts/min spikes."""
from datetime import datetime, timedelta


def detect(data: dict) -> dict:
    trade_log = data.get("trade_log", [])
    chain = data.get("chain", {})
    alerts = []
    top_score = 0

    now = datetime.now()
    last_60s = [t for t in trade_log if _parse(t["time"]) > now - timedelta(seconds=60)]
    last_20m = [t for t in trade_log if _parse(t["time"]) > now - timedelta(minutes=20)]

    # Group by strike+side
    groups: dict[str, dict] = {}
    for t in last_60s:
        key = f"{int(t['strike'])} {t['side']}"
        if key not in groups:
            groups[key] = {"contracts": 0, "buy_count": 0, "total": 0}
        groups[key]["contracts"] += t["size"]
        groups[key]["total"] += 1
        if t.get("is_buy"):
            groups[key]["buy_count"] += 1

    baseline_groups: dict[str, int] = {}
    for t in last_20m:
        key = f"{int(t['strike'])} {t['side']}"
        baseline_groups[key] = baseline_groups.get(key, 0) + t["size"]

    for key, g in groups.items():
        current_vel = g["contracts"]  # per minute (60s window)
        baseline_total = baseline_groups.get(key, 0)
        baseline_vel = max(1, baseline_total / 20)  # per minute avg
        multiple = current_vel / baseline_vel

        if multiple < 3:
            continue

        buy_pct = g["buy_count"] / g["total"] if g["total"] > 0 else 0.5
        if multiple >= 10:
            status = "CRITICAL"
            sc = 85 + min(15, (multiple - 10) / 10 * 15)
        else:
            status = "WATCH"
            sc = 30 + (multiple - 3) / 7 * 55

        sc = min(100, sc)
        top_score = max(top_score, sc)
        direction = f"{int(buy_pct*100)}% BUY SIDE" if buy_pct > 0.6 else f"{int((1-buy_pct)*100)}% SELL SIDE"

        alerts.append({
            "strike": key,
            "velocity": current_vel,
            "baseline": round(baseline_vel, 1),
            "multiple": f"{multiple:.1f}x",
            "direction": direction,
            "status": status,
            "score": round(sc, 1),
        })

    alerts.sort(key=lambda a: a["score"], reverse=True)
    best = alerts[0] if alerts else None

    return {
        "id": "d05_velocity",
        "name": "T&S Velocity",
        "score": round(top_score, 1),
        "status": best["status"] if best else "NORMAL",
        "metric": f"{best['multiple']} spike" if best else "Normal",
        "alerts": alerts[:5],
    }


def _parse(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return datetime.now()
