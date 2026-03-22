"""Detector 14 — Max Pain & Expiry Tracker. Tracks where sellers want market to close."""


def detect(data: dict) -> dict:
    max_pain = data.get("max_pain", 24300)
    spot = data.get("spot", 24300)
    time_to_exp = data.get("time_to_expiry_mins", 1440)
    is_expiry = data.get("is_expiry_day", False)

    distance = spot - max_pain
    abs_dist = abs(distance)
    direction = "above" if distance > 0 else "below"

    # Score based on distance from max pain + time to expiry
    if abs_dist > 150:
        sc = 80
        status_text = "BUYERS OVERPOWERING SELLERS" if distance > 0 else "SELLERS DOMINATING"
        signal = "Sustained move OR violent reversal"
        prob = 67 if abs_dist < 250 else 55
    elif abs_dist > 75:
        sc = 50
        status_text = "MODERATE DEVIATION"
        signal = "Gravitational pull increasing"
        prob = 55
    else:
        sc = 20
        status_text = "NEAR MAX PAIN"
        signal = "Sellers in control"
        prob = 40

    if is_expiry:
        sc = min(100, sc * 1.3)
    if time_to_exp < 120:
        sc = min(100, sc * 1.2)

    status = "CRITICAL" if sc > 75 else "ALERT" if sc > 50 else "WATCH" if sc > 25 else "NORMAL"

    hours = int(time_to_exp // 60)
    mins = int(time_to_exp % 60)

    return {
        "id": "d14_max_pain",
        "name": "Max Pain",
        "score": round(sc, 1),
        "status": status,
        "metric": f"MP:{int(max_pain)} ({int(distance):+d}pts)",
        "alerts": [{
            "max_pain": int(max_pain),
            "spot": round(spot, 2),
            "distance": f"{int(distance):+d} pts {direction}",
            "time_to_expiry": f"{hours}h {mins}min",
            "status_text": status_text,
            "signal": signal,
            "probability": f"{prob}%",
            "is_expiry_day": is_expiry,
            "status": status,
        }],
    }
