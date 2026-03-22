"""Detector 2 — Order Flow Imbalance. Distinguishes aggressive BUYING vs SELLING."""


def detect(data: dict) -> dict:
    chain = data.get("chain", {})
    alerts = []
    top_score = 0

    for strike, sides in chain.items():
        for side_key in ("CE", "PE"):
            info = sides.get(side_key)
            if not info or info.get("volume", 0) < 500:
                continue
            buy_pct = info.get("buy_pct", 0.5)
            vol = info.get("volume", 0)

            if side_key == "CE":
                if buy_pct >= 0.80:
                    status = "CRITICAL"
                    sc = 90 + (buy_pct - 0.80) * 50
                elif buy_pct >= 0.65:
                    status = "ALERT"
                    sc = 50 + (buy_pct - 0.65) / 0.15 * 40
                else:
                    continue
                label = "STRONG BULLISH FLOW" if buy_pct >= 0.80 else "Bullish Imbalance"
            else:
                sell_pct = 1 - buy_pct
                if sell_pct >= 0.80:
                    status = "CRITICAL"
                    sc = 90 + (sell_pct - 0.80) * 50
                elif sell_pct >= 0.65:
                    status = "ALERT"
                    sc = 50 + (sell_pct - 0.65) / 0.15 * 40
                else:
                    continue
                buy_pct_display = buy_pct
                label = "Selling Pressure" if sell_pct >= 0.80 else "Mild Selling"

            sc = min(100, sc)
            top_score = max(top_score, sc)
            alerts.append({
                "strike": f"{int(strike)} {side_key}",
                "buy_pct": f"{int(buy_pct * 100)}%",
                "volume": vol,
                "label": label if side_key == "CE" else f"Buy Side: {int(buy_pct*100)}% ({label})",
                "status": status,
                "score": round(sc, 1),
            })

    alerts.sort(key=lambda a: a["score"], reverse=True)
    best = alerts[0] if alerts else None

    return {
        "id": "d02_order_flow",
        "name": "Order Flow Imbalance",
        "score": round(top_score, 1),
        "status": best["status"] if best else "NORMAL",
        "metric": best["label"] if best else "Balanced",
        "alerts": alerts[:5],
    }
