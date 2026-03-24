"""Multi-Timeframe Confluence Analyzer — matches long TF with short TF for trades.

Scoring logic:
- Weekly trend alignment: +30 points
- Daily level respect: +25 points
- Hourly momentum: +20 points
- 15m pattern: +15 points
- 3m/5m entry trigger: +10 points
Total 100 = EXTREME confidence trade
"""

from datetime import datetime


def analyze_mtf(timeframes: dict, spot: float, atm: int, chain_data: list | None = None) -> dict:
    """Analyze multi-timeframe confluence and generate trade signal.

    Args:
        timeframes: dict of timeframe_key -> analysis dict (from TimeframeEngine)
        spot: current spot price
        atm: current ATM strike
        chain_data: current chain_summary for OI-based levels

    Returns:
        MTF analysis with score, direction, trade setup, reasoning
    """
    if not timeframes or len(timeframes) < 2:
        return {
            "score": 0, "direction": "NEUTRAL", "confidence": "LOW",
            "trade": None, "reasoning": [], "timeframe_alignment": {},
            "key_levels": {}, "timestamp": datetime.now().isoformat(),
        }

    score = 0
    direction_votes = {"BULLISH": 0, "BEARISH": 0, "SIDEWAYS": 0}
    reasoning = []
    tf_alignment = {}

    # --- Weekly (30 points) ---
    weekly = timeframes.get("1w", {})
    if weekly.get("trend") == "BULLISH":
        score += 30
        direction_votes["BULLISH"] += 3
        reasoning.append("Weekly trend BULLISH — major uptrend intact")
    elif weekly.get("trend") == "BEARISH":
        score += 30
        direction_votes["BEARISH"] += 3
        reasoning.append("Weekly trend BEARISH — major downtrend")
    else:
        score += 5
        reasoning.append("Weekly SIDEWAYS — no clear major trend")
    tf_alignment["1w"] = weekly.get("trend", "UNKNOWN")

    # --- Daily (25 points) ---
    daily = timeframes.get("1d", {})
    if daily.get("trend") == "BULLISH":
        score += 25
        direction_votes["BULLISH"] += 2.5
        reasoning.append(f"Daily BULLISH — EMA9 > EMA21, strength {daily.get('trend_strength', 0):.0f}%")
    elif daily.get("trend") == "BEARISH":
        score += 25
        direction_votes["BEARISH"] += 2.5
        reasoning.append(f"Daily BEARISH — EMA9 < EMA21, strength {daily.get('trend_strength', 0):.0f}%")
    else:
        score += 5
    tf_alignment["1d"] = daily.get("trend", "UNKNOWN")

    # Daily breakout bonus
    if daily.get("breakout") in ("BREAKOUT UP", "REVERSAL UP"):
        score += 5
        direction_votes["BULLISH"] += 1
        reasoning.append(f"Daily {daily['breakout']} detected — momentum shift")
    elif daily.get("breakout") in ("BREAKOUT DOWN", "REVERSAL DOWN"):
        score += 5
        direction_votes["BEARISH"] += 1
        reasoning.append(f"Daily {daily['breakout']} detected — momentum shift")

    # --- Hourly (20 points) ---
    hourly = timeframes.get("1h", {})
    if hourly.get("trend"):
        if hourly["trend"] == "BULLISH":
            score += 20
            direction_votes["BULLISH"] += 2
            reasoning.append(f"1H BULLISH — near-term momentum up")
        elif hourly["trend"] == "BEARISH":
            score += 20
            direction_votes["BEARISH"] += 2
            reasoning.append(f"1H BEARISH — near-term momentum down")
        else:
            score += 5
    tf_alignment["1h"] = hourly.get("trend", "UNKNOWN")

    # --- 15 Min (15 points) ---
    m15 = timeframes.get("15m", {})
    if m15.get("trend"):
        if m15["trend"] == "BULLISH":
            score += 15
            direction_votes["BULLISH"] += 1.5
        elif m15["trend"] == "BEARISH":
            score += 15
            direction_votes["BEARISH"] += 1.5
        else:
            score += 3
    tf_alignment["15m"] = m15.get("trend", "UNKNOWN")

    # 15m pullback to support in uptrend = high probability entry
    if m15.get("nearest_support") and hourly.get("trend") == "BULLISH":
        if spot - m15["nearest_support"] < (spot * 0.003):  # within 0.3%
            score += 5
            reasoning.append(f"15m pullback to support {m15['nearest_support']} in hourly uptrend — ideal entry")

    # --- 3m/5m Entry (10 points) ---
    m5 = timeframes.get("5m", {})
    m3 = timeframes.get("3m", {})
    entry_tf = m3 if m3.get("trend") else m5

    if entry_tf.get("trend"):
        if entry_tf["trend"] == "BULLISH":
            score += 10
            direction_votes["BULLISH"] += 1
        elif entry_tf["trend"] == "BEARISH":
            score += 10
            direction_votes["BEARISH"] += 1
    tf_alignment["5m"] = m5.get("trend", "UNKNOWN")
    tf_alignment["3m"] = m3.get("trend", "UNKNOWN")

    # Volume confirmation
    if m5.get("volume_ratio", 0) > 1.5:
        score += 3
        reasoning.append(f"5m volume {m5['volume_ratio']:.1f}x above average — strong participation")

    # --- Determine overall direction ---
    bull_score = direction_votes["BULLISH"]
    bear_score = direction_votes["BEARISH"]
    direction = "BULLISH" if bull_score > bear_score + 1 else "BEARISH" if bear_score > bull_score + 1 else "NEUTRAL"

    # --- Alignment bonus: all timeframes agree ---
    trends = [v for v in tf_alignment.values() if v in ("BULLISH", "BEARISH")]
    if len(trends) >= 4 and len(set(trends)) == 1:
        score += 10
        reasoning.append(f"FULL ALIGNMENT — {len(trends)} timeframes agree {trends[0]}")

    score = min(100, score)

    # --- Confidence level ---
    confidence = "EXTREME" if score >= 85 else "HIGH" if score >= 70 else "MEDIUM" if score >= 50 else "LOW"

    # --- Key levels from all timeframes ---
    key_levels = {
        "weekly_support": weekly.get("nearest_support", 0),
        "weekly_resistance": weekly.get("nearest_resistance", 0),
        "daily_support": daily.get("nearest_support", 0),
        "daily_resistance": daily.get("nearest_resistance", 0),
        "hourly_support": hourly.get("nearest_support", 0),
        "hourly_resistance": hourly.get("nearest_resistance", 0),
        "m15_support": m15.get("nearest_support", 0),
        "m15_resistance": m15.get("nearest_resistance", 0),
    }

    # Find strongest support/resistance (closest to spot from multiple TFs)
    all_supports = [v for v in key_levels.values() if v > 0 and "support" in [k for k, val in key_levels.items() if val == v][0] if v < spot]
    all_resistances = [v for v in [key_levels.get("weekly_resistance", 0), key_levels.get("daily_resistance", 0), key_levels.get("hourly_resistance", 0)] if v > spot]

    nearest_support = max(all_supports) if all_supports else atm - 100
    nearest_resistance = min(all_resistances) if all_resistances else atm + 100

    # --- Generate trade setup ---
    trade = None
    if score >= 50 and direction != "NEUTRAL":
        is_bull = direction == "BULLISH"
        strike = atm if is_bull else atm
        entry_price = 0  # will be filled by brain signal

        # Risk based on nearest S/R
        sl_distance = abs(spot - nearest_support) if is_bull else abs(nearest_resistance - spot)
        target_distance = abs(nearest_resistance - spot) if is_bull else abs(spot - nearest_support)

        trade = {
            "direction": direction,
            "type": "BUY CE" if is_bull else "BUY PE",
            "strike": strike,
            "entry_zone": f"{spot - 10:.0f} — {spot + 10:.0f}",
            "target_spot": nearest_resistance if is_bull else nearest_support,
            "stoploss_spot": nearest_support if is_bull else nearest_resistance,
            "risk_reward": round(target_distance / sl_distance, 2) if sl_distance > 0 else 0,
            "timeframe_entry": "3m/5m",
            "timeframe_confirmation": "15m/1h",
        }

    return {
        "score": score,
        "direction": direction,
        "confidence": confidence,
        "trade": trade,
        "reasoning": reasoning,
        "timeframe_alignment": tf_alignment,
        "key_levels": key_levels,
        "nearest_support": nearest_support,
        "nearest_resistance": nearest_resistance,
        "timestamp": datetime.now().isoformat(),
    }
