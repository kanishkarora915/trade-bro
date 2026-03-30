"""Check Trades Engine — Detects pre-explosion setups by combining MTF + OI + Flow data.

Looks for:
1. OI buildup at key strikes (someone is positioning)
2. IV compression → expansion (volatility squeeze)
3. Price consolidation near S/R (range tightening)
4. Sudden OI unwinding (shorts covering / longs exiting)
5. Volume spike across multiple timeframes
6. Divergence between timeframes (short TF moving, long TF flat = trap potential)

Generates trade signals with: Strike, Reason, LTP, Entry, SL, Target, Status
"""

from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))


def _ist_now() -> datetime:
    return datetime.now(IST)


def _score_setup(factors: dict) -> float:
    """Score a potential trade setup 0-100 based on multiple factors."""
    score = 0
    # OI concentration at strike (max 25)
    if factors.get("oi_concentration", 0) > 0.15:
        score += min(25, factors["oi_concentration"] * 100)
    # Volume spike (max 20)
    vol_ratio = factors.get("vol_ratio", 1)
    if vol_ratio > 1.5:
        score += min(20, (vol_ratio - 1) * 15)
    # IV compression (max 15) — low IV = cheap options = potential explosion
    iv_rank = factors.get("iv_rank", 50)
    if iv_rank < 30:
        score += 15
    elif iv_rank < 50:
        score += 8
    # Trend alignment across timeframes (max 20)
    tf_alignment = factors.get("tf_alignment", 0)
    score += min(20, tf_alignment * 5)
    # OI change velocity (max 10)
    oi_velocity = factors.get("oi_velocity", 0)
    score += min(10, oi_velocity * 2)
    # Breakout proximity (max 10)
    if factors.get("near_breakout", False):
        score += 10
    return min(100, score)


def analyze_setups(chain: dict, spot: float, atm: int, zone_analysis: dict,
                   tf_data: dict, confluence: dict, detectors: dict,
                   index_id: str = "NIFTY", strike_step: int = 50) -> list[dict]:
    """Analyze all data sources and return potential trade setups.

    Returns list of trade setups sorted by score, each with:
    - strike, side (CE/PE), direction (BULL/BEAR)
    - entry, target, sl, ltp
    - score, reason (detailed why)
    - status (ACTIVE/WATCHING/EXPIRED)
    - timeframe_signals: which TFs agree
    """
    if not chain or spot <= 0:
        return []

    setups = []
    now = _ist_now()
    h, m = now.hour, now.minute

    # BLOCK signals outside market hours (9:15 - 15:30 IST)
    market_open = (h == 9 and m >= 15) or (10 <= h <= 14) or (h == 15 and m <= 30)
    if not market_open:
        return []

    strikes = sorted(chain.keys())
    if not strikes:
        return []

    # Gather data
    support = zone_analysis.get("support_zone", atm - strike_step * 2)
    resistance = zone_analysis.get("resistance_zone", atm + strike_step * 2)
    winner = zone_analysis.get("winner", "NEUTRAL")
    trap_zones = [t["strike"] for t in zone_analysis.get("trap_zones", [])]
    conf_score = confluence.get("score", 0)
    conf_dir = confluence.get("direction", "NEUTRAL")

    # Extract timeframe trends
    tf_trends = {}
    if tf_data:
        for tf_key, tf_info in tf_data.items():
            if isinstance(tf_info, dict):
                tf_trends[tf_key] = tf_info.get("trend", "UNKNOWN")

    # Count aligned timeframes
    bull_tfs = sum(1 for t in tf_trends.values() if t == "BULLISH")
    bear_tfs = sum(1 for t in tf_trends.values() if t == "BEARISH")
    total_tfs = len(tf_trends) or 1

    # Detect which side has momentum
    market_bias = "NEUTRAL"
    if bull_tfs / total_tfs > 0.6:
        market_bias = "BULLISH"
    elif bear_tfs / total_tfs > 0.6:
        market_bias = "BEARISH"

    # Total OI for normalization
    total_ce_oi = sum((chain[s].get("CE") or {}).get("oi", 0) for s in strikes)
    total_pe_oi = sum((chain[s].get("PE") or {}).get("oi", 0) for s in strikes)
    total_oi = total_ce_oi + total_pe_oi or 1

    # ---- SETUP 1: OI-based Support/Resistance Trade ----
    # If market is near support and PE selling is heavy → BUY CE
    if support and abs(spot - support) < strike_step * 2 and winner == "BUYERS":
        ce_strike = atm
        ce = chain.get(ce_strike, {}).get("CE", {})
        if ce and ce.get("last_price", 0) >= 2:
            ltp = ce["last_price"]
            factors = {
                "oi_concentration": (chain.get(support, {}).get("PE", {}).get("oi", 0)) / total_oi,
                "vol_ratio": ce.get("volume", 0) / max(1, ce.get("avg_5d_volume", 1)),
                "iv_rank": ce.get("iv", 30),
                "tf_alignment": bull_tfs,
                "near_breakout": spot > support,
            }
            score = _score_setup(factors)
            if score >= 30:
                setups.append({
                    "strike": f"{int(ce_strike)} CE",
                    "side": "CE",
                    "direction": "BULL",
                    "index": index_id,
                    "ltp": round(ltp, 1),
                    "entry": round(ltp, 1),
                    "target": round(ltp * 1.4, 1),
                    "sl": round(ltp * 0.72, 1),
                    "score": round(score, 1),
                    "status": "ACTIVE" if score >= 60 else "WATCHING",
                    "reason": f"Near support {int(support)}, PE selling heavy, {bull_tfs}/{total_tfs} TFs bullish",
                    "reason_details": [
                        f"Support at {int(support)} (heavy PE OI writing)",
                        f"Market bias: {market_bias} ({bull_tfs}/{total_tfs} timeframes agree)",
                        f"OI Concentration: {factors['oi_concentration']*100:.1f}% at support",
                        f"Winner: {winner}",
                    ],
                    "timeframes": {k: v for k, v in tf_trends.items()},
                    "time": now.strftime("%H:%M"),
                    "timestamp": now.isoformat(),
                })

    # ---- SETUP 2: Resistance Rejection Trade ----
    if resistance and abs(spot - resistance) < strike_step * 2 and winner == "SELLERS":
        pe_strike = atm
        pe = chain.get(pe_strike, {}).get("PE", {})
        if pe and pe.get("last_price", 0) >= 2:
            ltp = pe["last_price"]
            factors = {
                "oi_concentration": (chain.get(resistance, {}).get("CE", {}).get("oi", 0)) / total_oi,
                "vol_ratio": pe.get("volume", 0) / max(1, pe.get("avg_5d_volume", 1)),
                "iv_rank": pe.get("iv", 30),
                "tf_alignment": bear_tfs,
                "near_breakout": spot < resistance,
            }
            score = _score_setup(factors)
            if score >= 30:
                setups.append({
                    "strike": f"{int(pe_strike)} PE",
                    "side": "PE",
                    "direction": "BEAR",
                    "index": index_id,
                    "ltp": round(ltp, 1),
                    "entry": round(ltp, 1),
                    "target": round(ltp * 1.4, 1),
                    "sl": round(ltp * 0.72, 1),
                    "score": round(score, 1),
                    "status": "ACTIVE" if score >= 60 else "WATCHING",
                    "reason": f"Near resistance {int(resistance)}, CE selling heavy, {bear_tfs}/{total_tfs} TFs bearish",
                    "reason_details": [
                        f"Resistance at {int(resistance)} (heavy CE OI writing)",
                        f"Market bias: {market_bias} ({bear_tfs}/{total_tfs} timeframes agree)",
                        f"OI Concentration: {factors['oi_concentration']*100:.1f}% at resistance",
                        f"Winner: {winner}",
                    ],
                    "timeframes": {k: v for k, v in tf_trends.items()},
                    "time": now.strftime("%H:%M"),
                    "timestamp": now.isoformat(),
                })

    # ---- SETUP 3: Breakout Trade (any direction) ----
    # Check if multiple TFs show breakout
    breakout_ups = 0
    breakout_downs = 0
    if tf_data:
        for tf_key, tf_info in tf_data.items():
            if isinstance(tf_info, dict):
                bo = tf_info.get("breakout", "NONE")
                if bo == "BREAKOUT UP":
                    breakout_ups += 1
                elif bo == "BREAKOUT DOWN":
                    breakout_downs += 1

    if breakout_ups >= 2:
        # Multiple TFs breaking out upward
        otm_ce = atm + strike_step
        ce = chain.get(otm_ce, {}).get("CE", {})
        if ce and ce.get("last_price", 0) >= 2:
            ltp = ce["last_price"]
            score = min(100, 40 + breakout_ups * 15 + bull_tfs * 5)
            setups.append({
                "strike": f"{int(otm_ce)} CE",
                "side": "CE",
                "direction": "BULL",
                "index": index_id,
                "ltp": round(ltp, 1),
                "entry": round(ltp, 1),
                "target": round(ltp * 1.5, 1),
                "sl": round(ltp * 0.7, 1),
                "score": round(score, 1),
                "status": "ACTIVE",
                "reason": f"BREAKOUT UP in {breakout_ups} timeframes, momentum confirmed",
                "reason_details": [
                    f"Breakout UP detected in {breakout_ups} timeframes simultaneously",
                    f"Trend alignment: {bull_tfs}/{total_tfs} TFs bullish",
                    f"OTM CE selected for leverage: {int(otm_ce)} CE",
                    "Multiple TF breakout = high probability continuation",
                ],
                "timeframes": {k: v for k, v in tf_trends.items()},
                "time": now.strftime("%H:%M"),
                "timestamp": now.isoformat(),
            })

    if breakout_downs >= 2:
        otm_pe = atm - strike_step
        pe = chain.get(otm_pe, {}).get("PE", {})
        if pe and pe.get("last_price", 0) >= 2:
            ltp = pe["last_price"]
            score = min(100, 40 + breakout_downs * 15 + bear_tfs * 5)
            setups.append({
                "strike": f"{int(otm_pe)} PE",
                "side": "PE",
                "direction": "BEAR",
                "index": index_id,
                "ltp": round(ltp, 1),
                "entry": round(ltp, 1),
                "target": round(ltp * 1.5, 1),
                "sl": round(ltp * 0.7, 1),
                "score": round(score, 1),
                "status": "ACTIVE",
                "reason": f"BREAKOUT DOWN in {breakout_downs} timeframes, selling confirmed",
                "reason_details": [
                    f"Breakout DOWN detected in {breakout_downs} timeframes simultaneously",
                    f"Trend alignment: {bear_tfs}/{total_tfs} TFs bearish",
                    f"OTM PE selected: {int(otm_pe)} PE",
                    "Multiple TF breakout = high probability continuation",
                ],
                "timeframes": {k: v for k, v in tf_trends.items()},
                "time": now.strftime("%H:%M"),
                "timestamp": now.isoformat(),
            })

    # ---- SETUP 4: OI Unwinding / Short Covering Signal ----
    # Large negative OI change on CE side = short covering = bullish
    for s in strikes:
        ce = chain[s].get("CE") or {}
        pe = chain[s].get("PE") or {}
        ce_oi_chg = ce.get("oi_day_change", 0)
        pe_oi_chg = pe.get("oi_day_change", 0)

        # CE short covering: CE OI decreasing + CE price increasing = bullish
        if ce_oi_chg < -50000 and ce.get("net_change", 0) > 0 and abs(s - atm) <= strike_step * 2:
            ltp = ce.get("last_price", 0)
            if ltp >= 2:
                score = min(90, 50 + abs(ce_oi_chg) / 10000)
                setups.append({
                    "strike": f"{int(s)} CE",
                    "side": "CE",
                    "direction": "BULL",
                    "index": index_id,
                    "ltp": round(ltp, 1),
                    "entry": round(ltp, 1),
                    "target": round(ltp * 1.35, 1),
                    "sl": round(ltp * 0.75, 1),
                    "score": round(score, 1),
                    "status": "ACTIVE",
                    "reason": f"CE Short Covering at {int(s)} — OI dropped {ce_oi_chg:,.0f}",
                    "reason_details": [
                        f"CE OI at {int(s)} dropped by {abs(ce_oi_chg):,.0f} (short covering)",
                        f"CE price rising (+{ce.get('net_change', 0):.1f})",
                        "Short covering = existing bears closing positions = bullish",
                        f"Timeframe alignment: {bull_tfs}/{total_tfs} bullish",
                    ],
                    "timeframes": {k: v for k, v in tf_trends.items()},
                    "time": now.strftime("%H:%M"),
                    "timestamp": now.isoformat(),
                })
                break  # Only one short covering signal

        # PE long unwinding: PE OI decreasing + PE price falling = bullish (fear reducing)
        if pe_oi_chg < -50000 and pe.get("net_change", 0) < 0 and abs(s - atm) <= strike_step * 2:
            ce_atm = chain.get(atm, {}).get("CE", {})
            ltp = ce_atm.get("last_price", 0)
            if ltp >= 2:
                score = min(85, 45 + abs(pe_oi_chg) / 10000)
                setups.append({
                    "strike": f"{int(atm)} CE",
                    "side": "CE",
                    "direction": "BULL",
                    "index": index_id,
                    "ltp": round(ltp, 1),
                    "entry": round(ltp, 1),
                    "target": round(ltp * 1.35, 1),
                    "sl": round(ltp * 0.75, 1),
                    "score": round(score, 1),
                    "status": "WATCHING",
                    "reason": f"PE Long Unwinding at {int(s)} — fear reducing, OI dropped {pe_oi_chg:,.0f}",
                    "reason_details": [
                        f"PE OI at {int(s)} dropped by {abs(pe_oi_chg):,.0f} (long unwinding)",
                        "PE buyers exiting = fear reducing = market stabilizing",
                        f"ATM CE suggested for entry at {int(atm)}",
                    ],
                    "timeframes": {k: v for k, v in tf_trends.items()},
                    "time": now.strftime("%H:%M"),
                    "timestamp": now.isoformat(),
                })
                break

    # ---- SETUP 5: Trap Zone Warning ----
    for trap_strike in trap_zones[:2]:
        ce = chain.get(trap_strike, {}).get("CE") or {}
        pe = chain.get(trap_strike, {}).get("PE") or {}
        if ce.get("oi_day_change", 0) > 0 and pe.get("oi_day_change", 0) > 0:
            setups.append({
                "strike": f"{int(trap_strike)}",
                "side": "TRAP",
                "direction": "WARNING",
                "index": index_id,
                "ltp": spot,
                "entry": 0,
                "target": 0,
                "sl": 0,
                "score": 0,
                "status": "WARNING",
                "reason": f"⚠️ TRAP ZONE at {int(trap_strike)} — both CE & PE OI building",
                "reason_details": [
                    f"CE OI change: +{ce.get('oi_day_change', 0):,.0f}",
                    f"PE OI change: +{pe.get('oi_day_change', 0):,.0f}",
                    "Both sides building = market makers trapping directional traders",
                    "AVOID trading near this level — wait for breakout above or below",
                ],
                "timeframes": {},
                "time": now.strftime("%H:%M"),
                "timestamp": now.isoformat(),
            })

    # ---- SETUP 6: Confluence-based momentum trade ----
    if conf_score >= 70:
        bull = conf_dir == "BULLISH"
        strike_key = atm if bull else atm
        side_key = "CE" if bull else "PE"
        opt = chain.get(strike_key, {}).get(side_key, {})
        ltp = opt.get("last_price", 0)
        if ltp >= 2:
            # Get firing detectors as reasons
            firing = confluence.get("firing", [])
            critical_detectors = [f for f in firing if f.get("status") in ("CRITICAL", "ALERT")]
            reasons = [f"Confluence {conf_score:.0f}/100 ({conf_dir})", f"{len(critical_detectors)} detectors in CRITICAL/ALERT"]
            reasons += [f"{f['name']}: {f['metric']}" for f in critical_detectors[:3]]

            score = min(100, conf_score * 1.1)
            setups.append({
                "strike": f"{int(strike_key)} {side_key}",
                "side": side_key,
                "direction": "BULL" if bull else "BEAR",
                "index": index_id,
                "ltp": round(ltp, 1),
                "entry": round(ltp, 1),
                "target": round(ltp * 1.4, 1),
                "sl": round(ltp * 0.72, 1),
                "score": round(score, 1),
                "status": "ACTIVE",
                "reason": f"HIGH CONFLUENCE {conf_score:.0f}/100 — {len(critical_detectors)} detectors firing",
                "reason_details": reasons,
                "timeframes": {k: v for k, v in tf_trends.items()},
                "time": now.strftime("%H:%M"),
                "timestamp": now.isoformat(),
            })

    # Sort by score descending, remove duplicates by strike
    seen = set()
    unique = []
    for s in sorted(setups, key=lambda x: -x["score"]):
        key = f"{s['strike']}_{s['direction']}"
        if key not in seen:
            seen.add(key)
            unique.append(s)

    return unique[:8]  # Top 8 setups max
