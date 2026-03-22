"""Detector 11 — Synthetic Position Detector. CE buy + PE sell at same strike = synthetic long."""


def detect(data: dict) -> dict:
    chain = data.get("chain", {})
    trade_log = data.get("trade_log", [])
    alerts = []
    top_score = 0

    # Aggregate buy/sell volume per strike per side from trade log
    strike_flow: dict[float, dict] = {}
    for t in trade_log:
        s = t["strike"]
        side = t["side"]
        if s not in strike_flow:
            strike_flow[s] = {"CE_buy": 0, "CE_sell": 0, "PE_buy": 0, "PE_sell": 0}
        if t.get("is_buy"):
            strike_flow[s][f"{side}_buy"] += t["size"]
        else:
            strike_flow[s][f"{side}_sell"] += t["size"]

    for strike, flow in strike_flow.items():
        ce_buy = flow["CE_buy"]
        pe_sell = flow["PE_sell"]
        ce_sell = flow["CE_sell"]
        pe_buy = flow["PE_buy"]

        # Synthetic long: high CE buy + high PE sell
        if ce_buy > 200 and pe_sell > 200:
            ratio = min(ce_buy, pe_sell) / max(1, max(ce_buy, pe_sell))
            if ratio > 0.5:
                sc = min(100, 50 + ratio * 50)
                top_score = max(top_score, sc)
                alerts.append({
                    "strike": int(strike),
                    "type": "SYNTHETIC LONG",
                    "ce_buy_lots": ce_buy,
                    "pe_sell_lots": pe_sell,
                    "confidence": "HIGH" if ratio > 0.7 else "MEDIUM",
                    "signal": "Institutional bullish bet",
                    "status": "CRITICAL" if ratio > 0.7 else "ALERT",
                    "score": round(sc, 1),
                })

        # Synthetic short: high CE sell + high PE buy
        if ce_sell > 200 and pe_buy > 200:
            ratio = min(ce_sell, pe_buy) / max(1, max(ce_sell, pe_buy))
            if ratio > 0.5:
                sc = min(100, 50 + ratio * 50)
                top_score = max(top_score, sc)
                alerts.append({
                    "strike": int(strike),
                    "type": "SYNTHETIC SHORT",
                    "ce_sell_lots": ce_sell,
                    "pe_buy_lots": pe_buy,
                    "confidence": "HIGH" if ratio > 0.7 else "MEDIUM",
                    "signal": "Institutional bearish bet",
                    "status": "CRITICAL" if ratio > 0.7 else "ALERT",
                    "score": round(sc, 1),
                })

    alerts.sort(key=lambda a: a["score"], reverse=True)
    best = alerts[0] if alerts else None

    return {
        "id": "d11_synthetic",
        "name": "Synthetic Position",
        "score": round(top_score, 1),
        "status": best["status"] if best else "NORMAL",
        "metric": best["type"] if best else "None",
        "alerts": alerts[:5],
    }
