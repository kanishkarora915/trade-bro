"""Detector 15 — Nifty-BankNifty Correlation Break."""


def detect(data: dict) -> dict:
    bn = data.get("banknifty", {})
    nifty_chg = bn.get("nifty_change_pct", 0)
    expected_bn = bn.get("expected_bn_change_pct", 0)
    actual_bn = bn.get("actual_bn_change_pct", 0)

    deviation = abs(actual_bn - expected_bn)

    if deviation > 1.0:
        status = "ALERT"
        sc = 70 + min(30, deviation * 10)
        signal = "MAJOR DIVERGENCE"
    elif deviation > 0.5:
        status = "WATCH"
        sc = 30 + deviation * 40
        signal = "DIVERGENCE STARTING"
    else:
        status = "NORMAL"
        sc = 0
        signal = "Correlated"

    # Determine opportunity
    if actual_bn < expected_bn - 0.5:
        opp = "BankNifty PE opportunity"
        event = "BANKING SPECIFIC EVENT"
    elif actual_bn > expected_bn + 0.5:
        opp = "BankNifty CE opportunity"
        event = "BANKING OUTPERFORMANCE"
    else:
        opp = ""
        event = ""

    return {
        "id": "d15_correlation",
        "name": "Nifty-BN Corr",
        "score": round(min(100, sc), 1),
        "status": status,
        "metric": signal,
        "alerts": [{
            "nifty_change": f"{nifty_chg:+.2f}%",
            "expected_bn": f"{expected_bn:+.2f}%",
            "actual_bn": f"{actual_bn:+.2f}%",
            "deviation": f"{deviation:.2f}%",
            "event": event,
            "opportunity": opp,
            "status": status,
        }] if sc > 0 else [],
    }
