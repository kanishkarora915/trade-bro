"""Detector 7 — Block Print / Dark Trade Identifier. Catches single massive trades (300+ lots)."""


def detect(data: dict) -> dict:
    trade_log = data.get("trade_log", [])
    alerts = []
    top_score = 0

    for t in trade_log:
        size = t.get("size", 0)
        if size < 300:
            continue

        if size >= 1500:
            status = "CRITICAL"
            label = "DARK PRINT"
            sc = 90 + min(10, (size - 1500) / 1500 * 10)
        elif size >= 700:
            status = "ALERT"
            label = "BLOCK PRINT"
            sc = 60 + (size - 700) / 800 * 30
        else:
            status = "WATCH"
            label = "LARGE TRADE"
            sc = 25 + (size - 300) / 400 * 35

        sc = min(100, sc)
        top_score = max(top_score, sc)

        alerts.append({
            "time": t["time"],
            "strike": f"{int(t['strike'])} {t['side']}",
            "size": size,
            "side_dir": "BUY" if t.get("is_buy") else "SELL",
            "label": label,
            "classification": "INSTITUTIONAL",
            "status": status,
            "score": round(sc, 1),
        })

    alerts.sort(key=lambda a: a["score"], reverse=True)
    best = alerts[0] if alerts else None

    return {
        "id": "d07_block_print",
        "name": "Block Print",
        "score": round(top_score, 1),
        "status": best["status"] if best else "NORMAL",
        "metric": f"{best['size']} lots {best['label']}" if best else "No blocks",
        "alerts": alerts[:5],
    }
