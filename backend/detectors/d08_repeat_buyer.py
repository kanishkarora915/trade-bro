"""Detector 8 — Repeat Buyer Fingerprint. Finds stealth accumulation — same size repeating."""


def detect(data: dict) -> dict:
    trade_log = data.get("trade_log", [])
    alerts = []
    top_score = 0

    # Group trades by strike+side
    groups: dict[str, list[dict]] = {}
    for t in trade_log:
        if not t.get("is_buy"):
            continue
        key = f"{int(t['strike'])} {t['side']}"
        groups.setdefault(key, []).append(t)

    for key, trades in groups.items():
        if len(trades) < 3:
            continue

        sizes = [t["size"] for t in trades]
        # Cluster by size (within 20%)
        clusters: list[list[int]] = []
        for s in sizes:
            placed = False
            for c in clusters:
                avg = sum(c) / len(c)
                if abs(s - avg) / avg <= 0.2:
                    c.append(s)
                    placed = True
                    break
            if not placed:
                clusters.append([s])

        for cluster in clusters:
            n = len(cluster)
            if n < 3:
                continue

            avg_size = int(sum(cluster) / n)
            if n >= 5:
                status = "CRITICAL"
                sc = 80 + min(20, (n - 5) * 5)
                pattern = "CONFIRMED ACCUMULATION"
            else:
                status = "WATCH"
                sc = 40 + (n - 3) * 20
                pattern = "STEALTH BUY"

            sc = min(100, sc)
            top_score = max(top_score, sc)

            alerts.append({
                "strike": key,
                "count": n,
                "avg_size": avg_size,
                "pattern": pattern,
                "status": status,
                "score": round(sc, 1),
            })

    alerts.sort(key=lambda a: a["score"], reverse=True)
    best = alerts[0] if alerts else None

    return {
        "id": "d08_repeat_buyer",
        "name": "Repeat Buyer",
        "score": round(top_score, 1),
        "status": best["status"] if best else "NORMAL",
        "metric": f"{best['count']}x repeat" if best else "No pattern",
        "alerts": alerts[:5],
    }
