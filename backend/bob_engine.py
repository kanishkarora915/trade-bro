"""Bob the Buyer — Dedicated Option BUYER Signal Engine.

Strict gate filters (IVR, GEX, Momentum) → Accumulation check → Momentum check →
Confluence scoring → Context boost → Position sizing.

Capital: ₹4,00,000 | Max Risk: 2% (₹8,000) | Hard SL: 40% premium drop.
Only generates BUY signals. Never sells, never shorts, never averages.
"""

import math
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

# ── Config ──
CAPITAL = 400000
MAX_RISK_PCT = 0.02
MAX_RISK = CAPITAL * MAX_RISK_PCT  # ₹8,000
SL_PCT = 0.40  # Exit when premium falls 40%
T1_MULT = 1.80  # +80% profit
T2_MULT = 2.50  # +150% profit

LOT_SIZES = {"NIFTY": 65, "BANKNIFTY": 30, "SENSEX": 20}

# ── Detector groups ──
ACCUMULATION_DETECTORS = ["d02_order_flow", "d03_sweep", "d08_repeat_buyer"]
MOMENTUM_DETECTORS = ["d05_velocity", "d12_greeks", "d01_uoa"]
CONTEXT_DETECTORS = ["d04_iv_divergence", "d09_skew_shift", "d15_correlation", "d17_fii_dii"]
TRAPPED_SELLER = "d07_block_print"
IGNORE_DETECTORS = {"d10_bid_ask", "d11_synthetic", "d14_max_pain", "d16_vacuum"}


# ── Black-Scholes Gamma (reused from d12_greeks) ──
_SQRT2PI = math.sqrt(2 * math.pi)

def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / _SQRT2PI

def _bs_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0 or S <= 0:
        return 0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return _norm_pdf(d1) / (S * sigma * math.sqrt(T))


def _is_fired(det: dict) -> bool:
    """Detector counts as fired if ALERT or CRITICAL."""
    return det.get("status") in ("ALERT", "CRITICAL")


def _calc_ivr(chain: dict, atm: float, step: float) -> tuple[float, str]:
    """Calculate IV Rank from chain. Returns (ivr_value, gate_status)."""
    ivs = []
    for strike, sides in chain.items():
        for side_key in ("CE", "PE"):
            info = sides.get(side_key)
            if info and info.get("iv", 0) > 0:
                ivs.append(info["iv"])
    if len(ivs) < 4:
        return 50.0, "YELLOW"

    # ATM IV = average of ATM CE + PE
    atm_ce = chain.get(atm, {}).get("CE", {}).get("iv", 0)
    atm_pe = chain.get(atm, {}).get("PE", {}).get("iv", 0)
    current_iv = (atm_ce + atm_pe) / 2 if (atm_ce > 0 and atm_pe > 0) else (atm_ce or atm_pe)

    min_iv = min(ivs)
    max_iv = max(ivs)
    if max_iv == min_iv:
        return 50.0, "YELLOW"

    ivr = ((current_iv - min_iv) / (max_iv - min_iv)) * 100
    ivr = max(0, min(100, ivr))

    if ivr > 40:
        status = "RED"
    elif ivr > 30:
        status = "YELLOW"
    else:
        status = "GREEN"
    return round(ivr, 1), status


def _calc_gex(chain: dict, spot: float, time_to_exp_mins: float, lot_size: int) -> tuple[float, float, float, str]:
    """Calculate Net GEX. Returns (ce_gex, pe_gex, net_gex, gate_status)."""
    r = 0.065
    T = max(time_to_exp_mins / (365 * 24 * 60), 0.0001)
    total_ce_gex = 0.0
    total_pe_gex = 0.0

    for strike, sides in chain.items():
        for side_key, multiplier in [("CE", 1), ("PE", -1)]:
            info = sides.get(side_key)
            if not info or info.get("iv", 0) <= 0:
                continue
            sigma = info["iv"] / 100
            oi = info.get("oi", 0)
            if oi <= 0:
                continue
            gamma = _bs_gamma(spot, float(strike), T, r, sigma)
            gex = gamma * oi * lot_size * 100  # normalized
            if side_key == "CE":
                total_ce_gex += gex
            else:
                total_pe_gex += gex

    net_gex = total_ce_gex - total_pe_gex
    # Positive GEX = dealers hedging = market pins = BAD for buyers
    # Negative GEX = dealers stop hedging = market accelerates = GOOD for buyers
    gate = "GREEN" if net_gex < 0 else "RED"
    return round(total_ce_gex, 0), round(total_pe_gex, 0), round(net_gex, 0), gate


def _check_momentum_gate(chain: dict, atm: float, direction: str) -> tuple[bool, str]:
    """Gate 3: Price move + Volume spike + OI increase must ALL occur."""
    side = "CE" if direction != "BEARISH" else "PE"
    # Check ATM and ATM±1 strikes
    checks = []
    for offset in [-1, 0, 1]:
        strike = atm + offset * 50  # approximate
        info = chain.get(strike, {}).get(side, {})
        if not info:
            continue
        price_up = info.get("net_change", 0) > 0
        vol_up = info.get("volume", 0) > info.get("avg_5d_volume", 1) * 1.2
        oi_up = info.get("oi_day_change", 0) > 0
        checks.append((price_up, vol_up, oi_up))

    if not checks:
        return False, "No data at ATM strikes"

    # At least one strike must have ALL 3
    for price_up, vol_up, oi_up in checks:
        if price_up and vol_up and oi_up:
            return True, "Price + Volume + OI confirmed"

    # Check what's missing
    any_price = any(c[0] for c in checks)
    any_vol = any(c[1] for c in checks)
    any_oi = any(c[2] for c in checks)
    missing = []
    if not any_price:
        missing.append("Price")
    if not any_vol:
        missing.append("Volume")
    if not any_oi:
        missing.append("OI")
    return False, f"Missing: {', '.join(missing) if missing else 'No simultaneous confirmation'}"


def _pick_strike(chain: dict, spot: float, atm: float, direction: str, step: int) -> tuple[float, float, dict] | None:
    """Pick best strike for buyer: ATM or 1 OTM, premium ≥ ₹5."""
    side = "CE" if direction != "BEARISH" else "PE"
    candidates = []

    for strike, sides in chain.items():
        info = sides.get(side)
        if not info or info.get("last_price", 0) < 5:
            continue
        ltp = info["last_price"]
        # Only ATM and 1-2 OTM
        if side == "CE" and strike < atm:
            continue  # skip ITM calls
        if side == "PE" and strike > atm:
            continue  # skip ITM puts
        dist = abs(strike - atm) / step
        if dist > 2:
            continue  # max 2 OTM
        # Score: prefer ATM, then 1 OTM
        score = 100 - dist * 20 + info.get("volume", 0) / 10000
        candidates.append((strike, ltp, info, score))

    if not candidates:
        return None
    candidates.sort(key=lambda x: -x[3])
    best = candidates[0]
    return best[0], best[1], best[2]


def generate(detectors: dict, chain: dict, spot: float, atm: int,
             india_vix: float, fii_dii: dict, time_to_expiry_mins: float,
             index_id: str = "NIFTY", lot_size: int = 75,
             strike_step: int = 50, confluence_direction: str = "NEUTRAL") -> dict:
    """Main Bob the Buyer signal engine. Returns complete signal dict with ALL sections always populated."""

    now = datetime.now(IST)
    h, m = now.hour, now.minute
    lot_size = LOT_SIZES.get(index_id, lot_size)
    direction = confluence_direction if confluence_direction != "NEUTRAL" else "BULLISH"
    side = "CE" if direction == "BULLISH" else "PE"

    # ══════════════════════════════════════════
    #  ALWAYS compute all data upfront — never skip sections
    # ══════════════════════════════════════════

    # GATES (always calculated)
    ivr_value, ivr_gate = _calc_ivr(chain, atm, strike_step)
    gate_ivr = {"value": ivr_value, "status": ivr_gate,
                "detail": f"IVR {ivr_value:.0f}% — {'Premium cheap' if ivr_gate == 'GREEN' else 'Premium expensive' if ivr_gate == 'RED' else 'Moderate'}"}

    ce_gex, pe_gex, net_gex, gex_gate = _calc_gex(chain, spot, time_to_expiry_mins, lot_size)
    gate_gex = {"ce_gex": ce_gex, "pe_gex": pe_gex, "net_gex": net_gex, "status": gex_gate,
                "detail": f"Net GEX: {net_gex:,.0f} — {'Negative = Buyer Zone' if net_gex < 0 else 'Positive = Market Pins'}"}

    mom_pass, mom_detail = _check_momentum_gate(chain, atm, direction)
    gate_mom = {"passed": mom_pass, "status": "GREEN" if mom_pass else "RED", "detail": mom_detail}

    gates = {"ivr": gate_ivr, "gex": gate_gex, "momentum": gate_mom}

    # ACCUMULATION DETECTORS (always calculated)
    accum_results = {}
    accum_fired = 0
    for det_id in ACCUMULATION_DETECTORS:
        det = detectors.get(det_id, {})
        fired = _is_fired(det)
        accum_results[det_id] = {"name": det.get("name", det_id), "fired": fired,
                                  "status": det.get("status", "NORMAL"), "metric": det.get("metric", ""),
                                  "score": det.get("score", 0)}
        if fired:
            accum_fired += 1

    # MOMENTUM DETECTORS (always calculated)
    mom_results = {}
    mom_fired = 0
    for det_id in MOMENTUM_DETECTORS:
        det = detectors.get(det_id, {})
        fired = _is_fired(det)
        mom_results[det_id] = {"name": det.get("name", det_id), "fired": fired,
                                "status": det.get("status", "NORMAL"), "metric": det.get("metric", ""),
                                "score": det.get("score", 0)}
        if fired:
            mom_fired += 1

    # CONTEXT DETECTORS (always calculated)
    context = {}
    for det_id in CONTEXT_DETECTORS:
        det = detectors.get(det_id, {})
        context[det_id] = {"name": det.get("name", det_id), "fired": _is_fired(det),
                           "status": det.get("status", "NORMAL"), "metric": det.get("metric", ""),
                           "score": det.get("score", 0)}

    # D07 TRAPPED SELLER (always calculated)
    trapped = detectors.get(TRAPPED_SELLER, {})
    trapped_fired = _is_fired(trapped)
    context[TRAPPED_SELLER] = {"name": "Trapped Seller (D07)", "fired": trapped_fired,
                                "status": trapped.get("status", "NORMAL"), "metric": trapped.get("metric", ""),
                                "score": trapped.get("score", 0)}

    # CONFLUENCE SCORE (always calculated)
    confluence = accum_fired + mom_fired
    context_fired = sum(1 for c in context.values() if c["fired"])

    # FIRED LIST (always calculated)
    fired_list = []
    for det_id in ACCUMULATION_DETECTORS + MOMENTUM_DETECTORS:
        r = accum_results.get(det_id) or mom_results.get(det_id, {})
        if r.get("fired"):
            fired_list.append(r["name"])

    # Missing list
    missing_accum = [accum_results[d]["name"] for d in ACCUMULATION_DETECTORS if not accum_results[d]["fired"]]
    missing_mom = [mom_results[d]["name"] for d in MOMENTUM_DETECTORS if not mom_results[d]["fired"]]
    all_missing = missing_accum + missing_mom

    # Base result — ALL sections always present
    base = {
        "gates": gates,
        "accumulation": accum_results,
        "momentum_det": mom_results,
        "context": context,
        "confluence_score": confluence,
        "accum_fired": accum_fired,
        "mom_fired": mom_fired,
        "fired": fired_list,
        "missing": all_missing,
        "spot": round(spot, 2),
        "atm": atm,
        "ivr": ivr_value,
        "net_gex": net_gex,
        "direction": direction,
        "side": side,
        "index": index_id,
        "timestamp": now.isoformat(),
        "position": None,
        "conviction": "NONE",
    }

    # ══════════════════════════════════════════
    #  SIGNAL DECISION — gates → detectors → confluence
    # ══════════════════════════════════════════

    # Market hours check
    market_active = (h == 9 and m >= 18) or (10 <= h <= 14) or (h == 15 and m < 20)
    if not market_active:
        return {**base, "signal": "WAIT", "reason": "Market closed — Bob only trades 9:18-15:20 IST",
                "watch_for": "Market to open at 9:18 AM IST"}

    # Gate 1: IVR
    if ivr_gate == "RED":
        return {**base, "signal": "WAIT",
                "reason": "GATE 1 BLOCKED — IVR above 40%. Premium too expensive. IV crush will destroy the trade.",
                "watch_for": "IVR to drop below 40%"}

    # Gate 2: GEX
    if gex_gate == "RED":
        return {**base, "signal": "WAIT",
                "reason": "GATE 2 BLOCKED — Positive GEX. Dealers hedging continuously, market will pin. Bad for buyers.",
                "watch_for": "GEX to flip negative"}

    # Gate 3: Momentum
    if not mom_pass:
        return {**base, "signal": "WAIT",
                "reason": f"GATE 3 BLOCKED — {mom_detail}. Need Price + Volume + OI all increasing simultaneously.",
                "watch_for": "All 3 momentum factors to align"}

    # Accumulation check
    if accum_fired < 2:
        return {**base, "signal": "WATCHLIST",
                "reason": f"Accumulation weak — only {accum_fired}/3 fired. Need 2 minimum."}

    # Momentum check
    if mom_fired < 2:
        return {**base, "signal": "WATCHLIST",
                "reason": f"Momentum weak — only {mom_fired}/3 fired. Need 2 minimum."}

    # Confluence check
    if confluence <= 3:
        return {**base, "signal": "WAIT",
                "reason": f"Confluence {confluence}/6 — too low. Need 5+ for BUY.",
                "watch_for": "More detectors to fire"}

    if confluence == 4:
        return {**base, "signal": "WATCHLIST",
                "reason": f"Confluence 4/6 — close but not enough. Watching..."}

    # IVR YELLOW + low confluence
    if ivr_gate == "YELLOW" and confluence < 5:
        return {**base, "signal": "WATCHLIST",
                "reason": f"IVR is YELLOW (30-40%). Need confluence 5+/6 but only have {confluence}/6."}

    # ══════════════════════════════════════════
    #  BUY / STRONG BUY — all gates passed, confluence 5+
    # ══════════════════════════════════════════
    signal_type = "STRONG BUY" if (confluence >= 6 or trapped_fired) else "BUY"

    if trapped_fired or (confluence == 6 and context_fired >= 2):
        conviction = "MAXIMUM"
    elif confluence >= 5 and context_fired >= 1:
        conviction = "HIGH"
    else:
        conviction = "MODERATE"

    # Pick strike + position sizing
    pick = _pick_strike(chain, spot, atm, direction, strike_step)
    if not pick:
        return {**base, "signal": "WAIT",
                "reason": "No suitable strike found — all premiums below ₹5 or no OTM available.",
                "watch_for": "Liquid OTM strike with premium ≥ ₹5"}

    strike, entry, info = pick
    sl = round(entry * (1 - SL_PCT), 2)
    t1 = round(entry * T1_MULT, 2)
    t2 = round(entry * T2_MULT, 2)

    risk_per_lot = (entry - sl) * lot_size
    if risk_per_lot <= 0:
        risk_per_lot = entry * SL_PCT * lot_size
    lots = max(1, int(MAX_RISK / risk_per_lot))
    capital_used = entry * lot_size * lots
    max_loss = round(risk_per_lot * lots, 0)

    reason_parts = [
        f"{confluence}/6 detectors confirmed — {', '.join(fired_list[:3])}.",
        f"GEX negative ({net_gex:,.0f}) = market accelerating, buyer zone.",
        f"IVR {ivr_value:.0f}% = premium {'cheap' if ivr_value < 30 else 'moderate'}.",
    ]
    if trapped_fired:
        reason_parts.insert(0, "TRAPPED SELLER detected — institutional short covering imminent. 80-100% premium return expected in 15-20 min.")

    return {
        **base,
        "signal": signal_type,
        "instrument": index_id,
        "strike": f"{int(strike)} {side}",
        "expiry": info.get("expiry", ""),
        "entry": round(entry, 1),
        "stop_loss": round(sl, 1),
        "target1": round(t1, 1),
        "target2": round(t2, 1),
        "lots": lots,
        "capital_used": round(capital_used, 0),
        "max_loss": round(max_loss, 0),
        "conviction": conviction,
        "reason": " ".join(reason_parts),
        "position": {
            "lots": lots,
            "lot_size": lot_size,
            "capital_used": round(capital_used, 0),
            "max_loss": round(max_loss, 0),
            "risk_per_lot": round(risk_per_lot, 0),
            "sl_pct": f"{SL_PCT * 100:.0f}%",
        },
    }


