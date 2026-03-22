"""Detector 13 — News-Price Reaction Mismatch. When market reacts opposite to news."""
import random


def detect(data: dict) -> dict:
    # In production, integrate with news API/RSS feeds
    # For now, simulate occasional mismatches
    spot = data.get("spot", 24300)
    trend = data.get("trend", 0)

    # Simulate a news mismatch ~15% of the time
    if random.random() < 0.15:
        if trend > 0:
            news = "Negative macro data released"
            expected = "DOWN"
            actual = "UP"
            signal = "HIDDEN HAND WAS LONG"
            follow = "More upside likely — follow the actual move"
            side = "CE Side Signal: ACTIVE"
        else:
            news = "RBI holds rates (Expected: Neutral/Up)"
            expected = "UP"
            actual = "DOWN"
            signal = "HIDDEN HAND WAS SHORT"
            follow = "More downside likely — follow the actual move"
            side = "PE Side Signal: ACTIVE"

        return {
            "id": "d13_news_mismatch",
            "name": "News Mismatch",
            "score": 70,
            "status": "ALERT",
            "metric": signal,
            "alerts": [{
                "news": news,
                "expected": expected,
                "actual": actual,
                "signal": signal,
                "follow": follow,
                "side": side,
                "status": "ALERT",
            }],
        }

    return {
        "id": "d13_news_mismatch",
        "name": "News Mismatch",
        "score": 0,
        "status": "NORMAL",
        "metric": "No mismatch",
        "alerts": [],
    }
