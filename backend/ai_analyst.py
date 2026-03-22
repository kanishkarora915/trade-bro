"""AI Analysis Bot — reads all 17 detectors + confluence + brain signal and generates
natural language trading suggestions.

Template-based NLP engine (no external API needed = zero latency).
Generates conversational Hinglish-English market commentary like a senior trader would.
"""

from datetime import datetime


def generate_analysis(
    detectors: dict,
    confluence: dict,
    brain: dict,
    spot: float,
    fii_dii: dict | None = None,
    index_name: str = "NIFTY",
) -> dict:
    """Generate full AI analysis from all detector outputs.

    Returns:
        {
            "summary": str,          # 1-2 line headline
            "analysis": str,         # Full paragraph analysis
            "bullets": list[str],    # Key points as bullets
            "sentiment": str,        # BULLISH / BEARISH / NEUTRAL / MIXED
            "confidence": str,       # HIGH / MEDIUM / LOW
            "risk_notes": list[str], # Risk warnings
            "timestamp": str,
        }
    """
    score = confluence.get("score", 0)
    direction = confluence.get("direction", "NEUTRAL")
    status = confluence.get("status", "NEUTRAL")
    firing = confluence.get("firing", [])

    # Collect detector insights
    active_detectors = []
    critical_detectors = []
    for det_id, result in detectors.items():
        det_score = result.get("score", 0)
        det_status = result.get("status", "NORMAL")
        if det_score > 30:
            active_detectors.append(result)
        if det_status in ("CRITICAL", "ALERT"):
            critical_detectors.append(result)

    # Build analysis components
    summary = _build_summary(score, direction, status, index_name, brain)
    analysis = _build_analysis(detectors, confluence, brain, spot, fii_dii, index_name)
    bullets = _build_bullets(critical_detectors, active_detectors, confluence, brain, fii_dii)
    risk_notes = _build_risks(detectors, confluence, brain)

    # Sentiment & confidence
    sentiment = direction if direction in ("BULLISH", "BEARISH") else "NEUTRAL"
    if len(critical_detectors) >= 3 and score >= 70:
        confidence = "HIGH"
    elif len(active_detectors) >= 5 and score >= 50:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return {
        "summary": summary,
        "analysis": analysis,
        "bullets": bullets[:8],
        "sentiment": sentiment,
        "confidence": confidence,
        "risk_notes": risk_notes[:4],
        "timestamp": datetime.now().isoformat(),
    }


def _build_summary(score: float, direction: str, status: str, index_name: str, brain: dict) -> str:
    """One-line headline."""
    if score >= 86:
        if direction == "BULLISH":
            return f"EXTREME BULLISH setup on {index_name} — Multiple detectors firing, institutional buying confirmed"
        elif direction == "BEARISH":
            return f"EXTREME BEARISH setup on {index_name} — Heavy selling pressure across detectors"
        return f"CRITICAL activity on {index_name} — Score {score:.0f}, direction unclear"

    if score >= 76:
        strike = brain.get("primary", {}).get("strike", "") if brain.get("active") else ""
        if direction == "BULLISH":
            return f"STRONG BULLISH signal on {index_name} {strike} — Confluence confirms upward momentum"
        elif direction == "BEARISH":
            return f"STRONG BEARISH signal on {index_name} {strike} — Downside pressure building"
        return f"HIGH ACTIVITY on {index_name} — Score {score:.0f}, monitor for direction clarity"

    if score >= 66:
        return f"MODERATE setup forming on {index_name} — {direction} bias, watching for confirmation"

    if score >= 51:
        return f"MILD activity on {index_name} — Early signs of {direction.lower()} positioning"

    return f"QUIET market on {index_name} — No significant detector activity, stay patient"


def _build_analysis(detectors: dict, confluence: dict, brain: dict, spot: float, fii_dii: dict | None, index_name: str) -> str:
    """Full paragraph analysis."""
    parts = []
    score = confluence.get("score", 0)
    direction = confluence.get("direction", "NEUTRAL")

    # Opening
    now = datetime.now()
    time_str = now.strftime("%I:%M %p")
    parts.append(f"As of {time_str}, {index_name} at {spot:,.0f}")

    # Score context
    if score >= 76:
        parts.append(f"with confluence score at {score:.0f} — this is a strong setup.")
    elif score >= 51:
        parts.append(f"with moderate confluence at {score:.0f}.")
    else:
        parts.append(f"is showing low activity (score {score:.0f}).")
        parts.append("No strong signals from any detector. Stay on the sidelines.")
        return " ".join(parts)

    # Key detector insights
    uoa = detectors.get("d01_uoa", {})
    flow = detectors.get("d02_order_flow", {})
    sweep = detectors.get("d03_sweep", {})
    block = detectors.get("d07_block_print", {})
    repeat = detectors.get("d08_repeat_buyer", {})
    iv_div = detectors.get("d04_iv_divergence", {})
    velocity = detectors.get("d05_velocity", {})
    fii_det = detectors.get("d17_fii_dii", {})
    max_pain = detectors.get("d14_max_pain", {})
    synth = detectors.get("d11_synthetic", {})
    skew = detectors.get("d09_skew_shift", {})

    # Unusual activity
    if uoa.get("score", 0) > 50:
        alerts = uoa.get("alerts", [])
        if alerts:
            top = alerts[0]
            parts.append(f"Unusual options activity detected on {top.get('strike', '?')} with {top.get('ratio', '?')}x volume spike.")

    # Order flow
    if flow.get("score", 0) > 50:
        alerts = flow.get("alerts", [])
        if alerts:
            top = alerts[0]
            parts.append(f"Order flow shows {top.get('buy_pct', '?')} buy-side on {top.get('strike', '?')} — {top.get('label', '')}.")

    # Sweep
    if sweep.get("score", 0) > 50:
        parts.append(f"Strike sweep detected — {sweep.get('metric', 'multiple strikes hit in quick succession')}. This is institutional-grade activity.")

    # Block print
    if block.get("score", 0) > 40:
        alerts = block.get("alerts", [])
        if alerts:
            top = alerts[0]
            parts.append(f"Block print: {top.get('size', 0)} lots on {top.get('strike', '?')} ({top.get('side_dir', 'UNKNOWN')}) — likely institutional.")

    # Repeat buyer
    if repeat.get("score", 0) > 40:
        parts.append(f"Repeat buyer pattern: {repeat.get('metric', 'stealth accumulation detected')}.")

    # IV
    if iv_div.get("score", 0) > 50:
        parts.append(f"IV divergence flagged — {iv_div.get('metric', 'unusual volatility pricing')}. Options are being priced for a move.")

    # Velocity
    if velocity.get("score", 0) > 50:
        parts.append(f"Volume velocity accelerating — {velocity.get('metric', 'contracts/min ramping')}.")

    # Synthetic
    if synth.get("score", 0) > 40:
        alerts = synth.get("alerts", [])
        if alerts:
            parts.append(f"Synthetic position detected: {alerts[0].get('type', 'complex strategy')} on {alerts[0].get('strikes', '?')}.")

    # Skew
    if skew.get("score", 0) > 40:
        parts.append(f"Skew shift: {skew.get('metric', 'IV tilt changing')} — directional bias confirmed.")

    # FII/DII
    if fii_dii and abs(fii_dii.get("fii_net_cr", 0)) > 500:
        fii = fii_dii["fii_net_cr"]
        dii = fii_dii.get("dii_net_cr", 0)
        if fii > 0:
            parts.append(f"FII net buying ₹{fii:,.0f} Cr today — macro bullish confirmation.")
        else:
            parts.append(f"FII net selling ₹{abs(fii):,.0f} Cr today.")
            if dii > 0:
                parts.append(f"DII supporting with ₹{dii:,.0f} Cr buying.")

    # Max pain
    if max_pain.get("score", 0) > 30:
        parts.append(f"Max pain level: {max_pain.get('metric', 'N/A')}.")

    # Trade recommendation
    if brain.get("active") and brain.get("primary"):
        p = brain["primary"]
        parts.append(f"\nTrade: BUY {p['strike']} at {p['cmp']}, Target {p['target1']}, SL {p['stop_loss']}.")
    elif score >= 51:
        parts.append(f"\nSetup is building but not confirmed yet. Wait for score to cross 76 for entry.")

    return " ".join(parts)


def _build_bullets(critical: list, active: list, confluence: dict, brain: dict, fii_dii: dict | None) -> list[str]:
    """Key point bullets."""
    bullets = []
    score = confluence.get("score", 0)
    direction = confluence.get("direction", "NEUTRAL")

    # Score
    bullets.append(f"Confluence Score: {score:.0f}/100 ({confluence.get('status', 'NEUTRAL')})")

    # Direction
    if direction != "NEUTRAL":
        bullets.append(f"Direction: {direction} — {len(critical)} detectors in CRITICAL/ALERT")

    # Critical detectors
    for det in critical[:3]:
        bullets.append(f"{det.get('name', '?')}: {det.get('metric', '')} [{det.get('status', '')}]")

    # FII/DII
    if fii_dii and fii_dii.get("source") != "unavailable":
        fii = fii_dii.get("fii_net_cr", 0)
        dii = fii_dii.get("dii_net_cr", 0)
        bullets.append(f"FII: ₹{fii:+,.0f} Cr | DII: ₹{dii:+,.0f} Cr")

    # Brain trade
    if brain.get("active") and brain.get("primary"):
        p = brain["primary"]
        bullets.append(f"BUY {p['strike']} @ {p['cmp']} → T1 {p['target1']} | SL {p['stop_loss']}")

    # Time multiplier
    tm = confluence.get("time_multiplier", 1)
    if tm > 1:
        bullets.append(f"Time boost active: {tm}x (high-impact trading window)")

    return bullets


def _build_risks(detectors: dict, confluence: dict, brain: dict) -> list[str]:
    """Risk warnings."""
    risks = []
    score = confluence.get("score", 0)

    # IV risk
    iv = detectors.get("d04_iv_divergence", {})
    if iv.get("score", 0) > 60:
        risks.append("IV is elevated — option premiums are expensive. Risk of IV crush if move doesn't happen fast.")

    # Bid-ask spread
    ba = detectors.get("d10_bid_ask", {})
    if ba.get("score", 0) > 50:
        risks.append(f"Wide bid-ask spreads detected — {ba.get('metric', 'liquidity is thin')}. Use limit orders.")

    # Correlation risk
    corr = detectors.get("d15_correlation", {})
    if corr.get("score", 0) > 50:
        risks.append(f"Cross-index divergence — {corr.get('metric', 'indices not moving together')}. Watch for false breakouts.")

    # Vacuum / gap risk
    vacuum = detectors.get("d16_vacuum", {})
    if vacuum.get("score", 0) > 50:
        risks.append(f"Price vacuum detected — {vacuum.get('metric', 'gap in liquidity')}. Stop loss may slip.")

    # Time decay
    if brain.get("active"):
        now = datetime.now()
        if now.hour >= 14 and now.minute >= 30:
            risks.append("Late session — theta decay accelerates. Tighten SL and take quick profits.")
        if confluence.get("is_expiry_day"):
            risks.append("EXPIRY DAY — Gamma risk is extreme. Widen SL or reduce position size.")

    # Score instability
    if 50 <= score <= 65:
        risks.append("Score is borderline — could flip either way. Don't go full size, use small entries.")

    if not risks:
        risks.append("No major risk flags. Follow standard exit rules.")

    return risks
