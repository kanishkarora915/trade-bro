"""Detector 10 — Bid-Ask Spread Widening. Market makers widen spreads as early warning."""


def detect(data: dict) -> dict:
    chain = data.get("chain", {})
    alerts = []
    top_score = 0

    for strike, sides in chain.items():
        for side_key in ("CE", "PE"):
            info = sides.get(side_key)
            if not info:
                continue
            bid = info.get("bid", 0)
            ask = info.get("ask", 0)
            if bid <= 0 or ask <= 0:
                continue
            spread = ask - bid
            baseline = info.get("spread_baseline", spread) or spread
            if baseline <= 0:
                continue

            ratio = spread / baseline
            if ratio < 2:
                continue

            widen_pct = int((ratio - 1) * 100)
            if ratio >= 3.5:
                status = "ALERT"
                sc = 75 + min(25, (ratio - 3.5) * 10)
            else:
                status = "WATCH"
                sc = 30 + (ratio - 2) / 1.5 * 45

            sc = min(100, sc)
            top_score = max(top_score, sc)
            alerts.append({
                "strike": f"{int(strike)} {side_key}",
                "spread": f"₹{spread:.2f}",
                "baseline": f"₹{baseline:.2f}",
                "widen_pct": f"{widen_pct}%",
                "status": status,
                "score": round(sc, 1),
            })

    alerts.sort(key=lambda a: a["score"], reverse=True)
    best = alerts[0] if alerts else None

    return {
        "id": "d10_bid_ask",
        "name": "Bid-Ask Spread",
        "score": round(top_score, 1),
        "status": best["status"] if best else "NORMAL",
        "metric": f"{best['widen_pct']} widen" if best else "Normal",
        "alerts": alerts[:5],
    }
