"""Confluence Score Engine — aggregates all 17 detectors into one master score."""
from datetime import datetime
from config import DETECTOR_WEIGHTS, TOTAL_MAX_POINTS


def _time_multiplier() -> float:
    now = datetime.now()
    h, m = now.hour, now.minute
    t = h * 60 + m

    if 555 <= t <= 570:  # 9:15 - 9:30
        return 1.2
    if 690 <= t <= 720:  # 11:30 - 12:00
        return 1.1
    if 840 <= t <= 870:  # 2:00 - 2:30
        return 1.1
    if 900 <= t <= 930:  # 3:00 - 3:30
        return 1.3
    return 1.0


def _status_label(score: float) -> str:
    if score >= 86:
        return "CRITICAL"
    if score >= 76:
        return "SIGNAL"
    if score >= 66:
        return "CAUTION"
    if score >= 51:
        return "WATCH"
    return "NEUTRAL"


def _status_color(score: float) -> str:
    if score >= 86:
        return "red"
    if score >= 76:
        return "orange"
    if score >= 66:
        return "yellow"
    if score >= 51:
        return "blue"
    return "grey"


def _direction(detector_results: dict) -> str:
    """Determine overall direction from confluence map and other detectors."""
    conf_map = detector_results.get("d06_confluence_map", {})
    direction = conf_map.get("direction", "NEUTRAL")

    # Boost with other directional signals
    bullish = 0
    bearish = 0

    skew = detector_results.get("d09_skew_shift", {})
    if "BULLISH" in skew.get("metric", ""):
        bullish += 2
    elif "BEARISH" in skew.get("metric", ""):
        bearish += 2

    synth = detector_results.get("d11_synthetic", {})
    for a in synth.get("alerts", []):
        if a.get("type") == "SYNTHETIC LONG":
            bullish += 3
        elif a.get("type") == "SYNTHETIC SHORT":
            bearish += 3

    fii = detector_results.get("d17_fii_dii", {})
    for a in fii.get("alerts", []):
        if "BULLISH" in a.get("signal", "").upper() or "buying" in a.get("signal", "").lower():
            bullish += 1
        elif "BEARISH" in a.get("signal", "").upper() or "selling" in a.get("signal", "").lower():
            bearish += 1

    if direction == "NEUTRAL":
        if bullish > bearish:
            direction = "BULLISH"
        elif bearish > bullish:
            direction = "BEARISH"

    return direction


def calculate(detector_results: dict, is_expiry_day: bool = False) -> dict:
    """Calculate master confluence score from all detector outputs."""
    raw_score = 0
    breakdown = {}
    firing = []

    for det_id, max_points in DETECTOR_WEIGHTS.items():
        result = detector_results.get(det_id, {})
        det_score = result.get("score", 0)
        # Scale detector score (0-100) to its weight
        weighted = (det_score / 100) * max_points
        raw_score += weighted
        breakdown[det_id] = {
            "name": result.get("name", det_id),
            "raw_score": det_score,
            "weighted": round(weighted, 2),
            "max": max_points,
            "status": result.get("status", "NORMAL"),
            "metric": result.get("metric", ""),
        }
        if det_score > 40:
            firing.append({
                "name": result.get("name", det_id),
                "metric": result.get("metric", ""),
                "status": result.get("status", "NORMAL"),
            })

    # Normalize to 100
    normalized = (raw_score / TOTAL_MAX_POINTS) * 100

    # FIX #8: Capped boosts — max 1.3x total (was 1.6x + 1.3x + 1.2x = 2.5x!!)
    critical_count = sum(1 for r in detector_results.values() if r.get("status") == "CRITICAL")
    alert_count = sum(1 for r in detector_results.values() if r.get("status") in ("CRITICAL", "ALERT"))
    boost = 1.0
    if critical_count >= 4:
        boost = 1.20
    elif critical_count >= 3:
        boost = 1.15
    elif critical_count >= 2:
        boost = 1.10

    # Time multiplier (capped) — removed arbitrary time boosts
    time_mult = 1.0  # FIX #8: no time boost, let data speak

    # Expiry day — no bonus (expiry = dangerous for buyers)
    # FIX #8: removed expiry bonus

    # Apply single capped boost
    normalized = min(100, normalized * boost)

    normalized = round(normalized, 1)

    direction = _direction(detector_results)

    firing.sort(key=lambda f: {"CRITICAL": 4, "ALERT": 3, "WATCH": 2, "NORMAL": 1}.get(f["status"], 0), reverse=True)

    return {
        "score": normalized,
        "status": _status_label(normalized),
        "color": _status_color(normalized),
        "direction": direction,
        "time_multiplier": time_mult,
        "is_expiry_day": is_expiry_day,
        "breakdown": breakdown,
        "firing": firing[:8],
        "timestamp": datetime.now().isoformat(),
    }
