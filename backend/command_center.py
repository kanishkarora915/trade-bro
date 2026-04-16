"""Command Center v2 — ONE brain, ONE signal, ONE voice.

Fixes from v1:
1. NET votes (bull - bear) for direction — no conflicting signals
2. IVR/GEX calculated directly (no Bob dependency)
3. Dynamic SL from OI walls (not fixed 15%)
4. Entry timing: pullback zone + breakout level
5. Detailed WAIT reasons with "what needs to change"

Capital: ₹10,00,000 | Max SL: 15% fallback | Lot sizes: NIFTY=75, BN=30, SENSEX=20
"""

import asyncio
import math
import time
import json
import os
from datetime import datetime, timezone, timedelta
from collections import deque
import telegram_alerts
from auto_tune import get_latest_report as get_tune_report
import trade_tracker

IST = timezone(timedelta(hours=5, minutes=30))

CAPITAL = 1000000
MAX_SL_PCT = 0.15
LOT_SIZES = {"NIFTY": 75, "BANKNIFTY": 30, "SENSEX": 20}
T1_MULT = 1.30
T2_MULT = 1.60

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))

_active_trade: dict | None = None
_trade_history: list[dict] = []
_position_alerts: deque = deque(maxlen=20)
_last_signal_ts: float = 0
_daily_pnl: float = 0  # running daily P&L
_daily_losses: int = 0  # consecutive losses today
_last_reset_date: str = ""
SIGNAL_COOLDOWN_NORMAL = 300   # 5 min normal
SIGNAL_COOLDOWN_TRENDING = 180 # 3 min trending
SIGNAL_COOLDOWN_RANGE = 600    # 10 min range
DAILY_LOSS_LIMIT = -20000      # ₹20K max daily loss
MAX_CONSECUTIVE_LOSSES = 3     # pause after 3 losses
COMMISSION_PER_LOT = 200       # ~₹200 per lot brokerage
SLIPPAGE_PCT = 0.005           # 0.5% slippage buffer
CONVICTION_CAP = 15            # max conviction score

# ── Inline IVR + GEX (no Bob dependency) ──
def _calc_ivr(chain: dict, atm: int) -> tuple[float, str]:
    ivs = []
    for strike, sides in chain.items():
        for sk in ("CE", "PE"):
            info = sides.get(sk)
            if info and info.get("iv", 0) > 0:
                ivs.append(info["iv"])
    if len(ivs) < 4:
        return 50.0, "YELLOW"
    atm_ce = chain.get(atm, {}).get("CE", {}).get("iv", 0)
    atm_pe = chain.get(atm, {}).get("PE", {}).get("iv", 0)
    current = (atm_ce + atm_pe) / 2 if (atm_ce > 0 and atm_pe > 0) else (atm_ce or atm_pe)
    mn, mx = min(ivs), max(ivs)
    if mx == mn:
        return 50.0, "YELLOW"
    ivr = max(0, min(100, ((current - mn) / (mx - mn)) * 100))
    return round(ivr, 1), "RED" if ivr > 40 else "YELLOW" if ivr > 30 else "GREEN"

def _norm_pdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)

def _calc_gex(chain: dict, spot: float, tte_mins: float, lot_size: int) -> tuple[float, str]:
    r, T = 0.065, max(tte_mins / (365 * 24 * 60), 0.0001)
    ce_gex = pe_gex = 0
    for strike, sides in chain.items():
        for sk, mult in [("CE", 1), ("PE", -1)]:
            info = sides.get(sk)
            if not info or info.get("iv", 0) <= 0:
                continue
            sigma = info["iv"] / 100
            oi = info.get("oi", 0)
            if oi <= 0 or sigma <= 0 or T <= 0 or spot <= 0:
                continue
            d1 = (math.log(spot / float(strike)) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
            gamma = _norm_pdf(d1) / (spot * sigma * math.sqrt(T))
            gex = gamma * oi * lot_size * 100
            if sk == "CE":
                ce_gex += gex
            else:
                pe_gex += gex
    net = ce_gex - pe_gex
    return round(net, 0), "GREEN" if net < 0 else "RED"

# ── Dynamic SL from actual chain premium at OI wall strike (FIX #1) ──
def _find_dynamic_sl(chain: dict, spot: float, atm: int, side: str, step: int, entry: float) -> tuple[float, str]:
    """Find SL from actual premium at OI wall strike. Returns (sl_price, sl_type)."""
    if side == "CE":
        # CE buy SL: find strongest PE OI wall below ATM (support)
        # When spot falls to wall, look up actual CE premium there
        walls = []
        for strike in sorted(chain.keys()):
            if strike >= atm - step:
                continue
            pe = chain[strike].get("PE", {})
            if pe.get("oi", 0) > 30000:
                walls.append((strike, pe["oi"]))
        if walls:
            best_wall = max(walls, key=lambda w: w[1])
            # Get CE premium at a strike near the wall (approximation)
            # If wall at 22200 and we bought 22350 CE, check 22350 CE premium
            # when spot would be at 22200 — use OTM premium as proxy
            wall_ce = chain.get(best_wall[0] + step, {}).get("CE", {})
            if wall_ce and wall_ce.get("last_price", 0) > 0:
                sl = round(wall_ce["last_price"] * 0.85, 1)  # 15% below wall premium
                return max(sl, entry * 0.70), "OI WALL"
            # Fallback: use delta-approximated premium at wall
            sl = round(entry * max(0.70, 1 - abs(spot - best_wall[0]) / spot * 1.5), 1)
            return sl, "OI WALL"
    else:
        walls = []
        for strike in sorted(chain.keys()):
            if strike <= atm + step:
                continue
            ce = chain[strike].get("CE", {})
            if ce.get("oi", 0) > 30000:
                walls.append((strike, ce["oi"]))
        if walls:
            best_wall = max(walls, key=lambda w: w[1])
            wall_pe = chain.get(best_wall[0] - step, {}).get("PE", {})
            if wall_pe and wall_pe.get("last_price", 0) > 0:
                sl = round(wall_pe["last_price"] * 0.85, 1)
                return max(sl, entry * 0.70), "OI WALL"
            sl = round(entry * max(0.70, 1 - abs(best_wall[0] - spot) / spot * 1.5), 1)
            return sl, "OI WALL"

    return round(entry * (1 - MAX_SL_PCT), 1), "FIXED 15%"

# ── Entry timing ──
def _calc_entry_zone(chain: dict, spot: float, atm: int, side: str, step: int, entry: float) -> dict:
    """Calculate pullback zone and breakout level."""
    if side == "CE":
        # Pullback zone: nearest PE OI wall = support → buy near that
        support = None
        for strike in sorted(chain.keys(), reverse=True):
            if strike >= atm:
                continue
            pe = chain[strike].get("PE", {})
            if pe.get("oi", 0) > 30000:
                support = strike
                break
        pullback_spot = support if support else atm - step
        pullback_premium = round(entry * 0.90, 1)  # ~10% below current

        # Breakout: nearest CE OI wall above = resistance → break above
        resistance = None
        for strike in sorted(chain.keys()):
            if strike <= atm:
                continue
            ce = chain[strike].get("CE", {})
            if ce.get("oi", 0) > 30000:
                resistance = strike
                break
        breakout_spot = resistance if resistance else atm + step * 2

        return {
            "pullback_zone": f"₹{pullback_premium:.0f}-{round(entry * 0.95, 1):.0f}",
            "pullback_spot": pullback_spot,
            "pullback_reason": f"Support at {pullback_spot} (PE OI wall). Wait for dip to enter cheaper.",
            "breakout_level": f"₹{round(entry * 1.10, 1):.0f}+",
            "breakout_spot": breakout_spot,
            "breakout_reason": f"If {breakout_spot} resistance breaks, momentum entry above ₹{round(entry * 1.10, 1):.0f}.",
            "avoid_above": f"₹{round(entry * 1.25, 1):.0f}",
            "avoid_reason": "Premium too expensive above this — risk/reward poor.",
        }
    else:
        resistance = None
        for strike in sorted(chain.keys()):
            if strike <= atm:
                continue
            ce = chain[strike].get("CE", {})
            if ce.get("oi", 0) > 30000:
                resistance = strike
                break
        pullback_premium = round(entry * 0.90, 1)

        support = None
        for strike in sorted(chain.keys(), reverse=True):
            if strike >= atm:
                continue
            pe = chain[strike].get("PE", {})
            if pe.get("oi", 0) > 30000:
                support = strike
                break
        breakdown_spot = support if support else atm - step * 2

        return {
            "pullback_zone": f"₹{pullback_premium:.0f}-{round(entry * 0.95, 1):.0f}",
            "pullback_spot": resistance or atm + step,
            "pullback_reason": f"Resistance at {resistance or atm + step}. Wait for bounce to enter cheaper.",
            "breakout_level": f"₹{round(entry * 1.10, 1):.0f}+",
            "breakout_spot": breakdown_spot,
            "breakout_reason": f"If {breakdown_spot} support breaks, momentum entry.",
            "avoid_above": f"₹{round(entry * 1.25, 1):.0f}",
            "avoid_reason": "Premium too expensive above this.",
        }


def _save_trade(trade: dict):
    try:
        trades_dir = os.path.join(DATA_DIR, "command_center")
        os.makedirs(trades_dir, exist_ok=True)
        date = datetime.now(IST).strftime("%Y-%m-%d")
        path = os.path.join(trades_dir, f"trades_{date}.json")
        existing = []
        if os.path.exists(path):
            with open(path) as f:
                existing = json.load(f)
        existing.append(trade)
        with open(path, "w") as f:
            json.dump(existing, f, default=str)
    except Exception:
        pass


def _load_today_trades() -> list[dict]:
    try:
        date = datetime.now(IST).strftime("%Y-%m-%d")
        path = os.path.join(DATA_DIR, "command_center", f"trades_{date}.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _pick_best_strike(chain: dict, spot: float, atm: int, side: str, step: int) -> dict | None:
    candidates = []
    for strike in sorted(chain.keys()):
        info = chain[strike].get(side)
        if not info or info.get("last_price", 0) < 10:
            continue
        ltp = info["last_price"]
        if side == "CE" and strike < atm: continue
        if side == "PE" and strike > atm: continue
        dist = abs(strike - atm) / step
        if dist > 3: continue
        vol = info.get("volume", 0)
        oi = info.get("oi", 0)
        score = 100 - dist * 15 + min(30, vol / 5000) + min(20, oi / 50000)
        candidates.append({"strike": int(strike), "ltp": ltp, "score": score, "vol": vol, "oi": oi})
    if not candidates:
        return None
    candidates.sort(key=lambda x: -x["score"])
    return candidates[0]


def generate(confluence: dict, detectors: dict, seller: dict, vpin: dict,
             trap: dict, dealer: dict, bob: dict, chain: dict,
             spot: float, atm: int, index_id: str = "NIFTY",
             strike_step: int = 50, market_intel: dict | None = None) -> dict:
    """Command Center v3 — NET votes, dynamic SL, entry timing, circuit breakers."""
    global _active_trade, _last_signal_ts, _daily_pnl, _daily_losses, _last_reset_date

    now = datetime.now(IST)
    now_ts = time.time()
    h, m = now.hour, now.minute
    lot_size = LOT_SIZES.get(index_id, 75)
    today = now.strftime("%Y-%m-%d")

    # Daily reset
    if today != _last_reset_date:
        _daily_pnl = 0
        _daily_losses = 0
        _last_reset_date = today

    market_active = (h == 9 and m >= 18) or (10 <= h <= 14) or (h == 15 and m < 20)

    # Adaptive cooldown based on regime
    regime_str = (market_intel or {}).get("regime", {}).get("regime", "UNKNOWN")
    if "TRENDING" in regime_str:
        cooldown = SIGNAL_COOLDOWN_TRENDING
    elif "RANGE" in regime_str:
        cooldown = SIGNAL_COOLDOWN_RANGE
    else:
        cooldown = SIGNAL_COOLDOWN_NORMAL

    # ══════════════════════════════════════════
    #  STEP 1: Collect votes from ALL sources
    # ══════════════════════════════════════════
    bull = 0
    bear = 0
    reasons_bull = []
    reasons_bear = []
    conviction = 0

    # A) Confluence (weight 3)
    conf_dir = confluence.get("direction", "NEUTRAL")
    conf_score = confluence.get("score", 0)
    if conf_dir == "BULLISH" and conf_score > 30:
        bull += 3
        reasons_bull.append(f"Confluence {conf_score:.0f}/100 BULLISH")
        conviction += min(3, conf_score / 30)
    elif conf_dir == "BEARISH" and conf_score > 30:
        bear += 3
        reasons_bear.append(f"Confluence {conf_score:.0f}/100 BEARISH")
        conviction += min(3, conf_score / 30)

    # B) Seller Footprint (weight 4)
    for sig in seller.get("signals", []):
        s = sig.get("signal", "")
        if "BUY CE" in s:
            bull += 4
            reasons_bull.append(f"Sellers: {sig.get('reason', '')[:60]}")
            conviction += 3 if sig.get("conviction") == "HIGH" else 2
        elif "BUY PE" in s:
            bear += 4
            reasons_bear.append(f"Sellers: {sig.get('reason', '')[:60]}")
            conviction += 3 if sig.get("conviction") == "HIGH" else 2
        elif "AVOID CE" in s:
            bear += 2
            reasons_bear.append("Heavy call writing — upside capped")

    # C) VPIN (weight 2)
    ce_vpin = vpin.get("ce_vpin", 0)
    pe_vpin = vpin.get("pe_vpin", 0)
    if ce_vpin > pe_vpin + 0.1:
        bull += 2
        reasons_bull.append(f"VPIN: CE toxic ({ce_vpin:.0%})")
    elif pe_vpin > ce_vpin + 0.1:
        bear += 2
        reasons_bear.append(f"VPIN: PE toxic ({pe_vpin:.0%})")

    # D) Dealer (weight 5)
    for sig in dealer.get("signals", []):
        w = 5 if sig.get("source") == "DEALER DELTA FLIP" else 4 if sig.get("source") == "DEALER PANIC" else 3
        if "CE" in sig.get("signal", "") and "AVOID" not in sig.get("signal", ""):
            bull += w
            reasons_bull.append(f"Dealer: {sig.get('reason', '')[:60]}")
            conviction += 4 if sig.get("conviction") == "MAXIMUM" else 3
        elif "PE" in sig.get("signal", ""):
            bear += w
            reasons_bear.append(f"Dealer: {sig.get('reason', '')[:60]}")
            conviction += 4 if sig.get("conviction") == "MAXIMUM" else 3

    # E) Trap (weight 3)
    for t in trap.get("traps", []):
        if t.get("side") == "CE":
            bull += 3
            reasons_bull.append(f"Trap reversal: {t['strike']} CE")
            conviction += 2
        elif t.get("side") == "PE":
            bear += 3
            reasons_bear.append(f"Trap reversal: {t['strike']} PE")
            conviction += 2

    # Cap conviction (FIX: no infinite conviction)
    conviction = min(conviction, CONVICTION_CAP)

    # ══════════════════════════════════════════
    #  STEP 2: NET direction (FIX #1 — no more conflicting signals)
    # ══════════════════════════════════════════
    net = bull - bear  # positive = bullish, negative = bearish
    abs_net = abs(net)
    total_votes = bull + bear

    if abs_net < 3 or total_votes == 0:
        direction = "NEUTRAL"
        strength = 0
    elif net > 0:
        direction = "BULLISH"
        strength = net / max(total_votes, 1)
    else:
        direction = "BEARISH"
        strength = abs(net) / max(total_votes, 1)

    side = "CE" if direction == "BULLISH" else "PE"
    reasons = reasons_bull if direction == "BULLISH" else reasons_bear

    # ══════════════════════════════════════════
    #  STEP 3: Gates (FIX #2 — direct IVR/GEX, no Bob)
    # ══════════════════════════════════════════
    mi = market_intel or {}
    regime = mi.get("regime", {}).get("regime", "UNKNOWN")
    trade_verdict = mi.get("tradeability", {}).get("verdict", "GO")
    tte = mi.get("expiry", {}).get("time_to_expiry_mins", 60)

    ivr_val, ivr_gate = _calc_ivr(chain, atm) if chain else (50, "YELLOW")
    net_gex, gex_gate = _calc_gex(chain, spot, tte, lot_size) if chain else (0, "GREEN")

    # ══════════════════════════════════════════
    #  STEP 4: Signal decision (FIX #1 — NET based)
    # ══════════════════════════════════════════
    signal = "WAIT"
    reason = ""
    wait_reasons = []  # FIX #5 — all blockers
    what_to_change = []

    # Expiry day auto-close (FIX #16)
    is_expiry = mi.get("expiry", {}).get("is_expiry", False)
    if is_expiry and h == 15 and m >= 15 and _active_trade:
        _active_trade["status"] = "EXPIRY_CLOSE"

    if not market_active:
        signal = "MARKET CLOSED"
        reason = "No trading outside 9:18-15:20 IST"
    else:
        # Circuit breaker (FIX #14)
        if _daily_losses >= MAX_CONSECUTIVE_LOSSES:
            wait_reasons.append(f"CIRCUIT BREAKER — {_daily_losses} consecutive losses. Paused 30 min.")
            what_to_change.append("Wait 30 min or next winning trade to reset")
        # Daily loss limit (FIX #15)
        if _daily_pnl <= DAILY_LOSS_LIMIT:
            wait_reasons.append(f"DAILY LOSS LIMIT — ₹{abs(_daily_pnl):,.0f} lost today. No more trades.")
            what_to_change.append("Tomorrow — fresh day, fresh capital")

        # Check all blockers
        if trade_verdict == "AVOID":
            wait_reasons.append(f"Market regime: {regime} — not tradeable")
            what_to_change.append("Market to start trending (break out of range)")
        if ivr_gate == "RED":
            wait_reasons.append(f"IVR {ivr_val:.0f}% — premium too expensive, IV crush risk")
            what_to_change.append("IVR to drop below 40% (premiums become cheaper)")
        if gex_gate == "RED":
            wait_reasons.append(f"GEX positive ({net_gex:,.0f}) — dealers hedging, market will pin")
            what_to_change.append("GEX to flip negative (dealers stop hedging)")
        if direction == "NEUTRAL":
            wait_reasons.append(f"Direction confused — Bull {bull} vs Bear {bear} (net {net:+d})")
            what_to_change.append("One side to dominate by 3+ votes")
        elif abs_net < 3:
            wait_reasons.append(f"Net too low ({net:+d}) — Bull {bull} vs Bear {bear}")
            what_to_change.append(f"Net votes to reach +5 or -5 (currently {net:+d})")

        if wait_reasons:
            signal = "WAIT"
            reason = " | ".join(wait_reasons[:3])
        elif abs_net >= 8 and conviction >= 8 and ivr_gate != "RED":
            signal = "STRONG BUY"
            reason = " | ".join(reasons[:3])
        elif abs_net >= 5 and conviction >= 5 and ivr_gate != "RED":
            signal = "BUY"
            reason = " | ".join(reasons[:3])
        elif abs_net >= 3:
            signal = "WATCHLIST"
            reason = f"Building — net {net:+d}. " + (reasons[0] if reasons else "")
            what_to_change.append(f"Net to reach ±5 for BUY (currently {net:+d})")

    # Cooldown
    if signal in ("BUY", "STRONG BUY"):
        if now_ts - _last_signal_ts < cooldown and _active_trade:
            if _active_trade.get("side") != side:
                signal = "WAIT"
                reason = f"Cooldown — active {_active_trade['side']} trade. {int(SIGNAL_COOLDOWN - (now_ts - _last_signal_ts))}s left."

    # ══════════════════════════════════════════
    #  STEP 5: Pick strike + dynamic SL + entry timing
    # ══════════════════════════════════════════
    trade = None
    entry_zone = None
    if signal in ("BUY", "STRONG BUY") and chain:
        pick = _pick_best_strike(chain, spot, atm, side, strike_step)
        if pick:
            raw_entry = pick["ltp"]
            # Add slippage (FIX #13)
            entry = round(raw_entry * (1 + SLIPPAGE_PCT), 1)

            # FIX #1: Dynamic SL from actual chain premium at OI wall
            sl, sl_type = _find_dynamic_sl(chain, spot, atm, side, strike_step, entry)
            t1 = round(entry * T1_MULT, 1)
            t2 = round(entry * T2_MULT, 1)
            risk_per_lot = (entry - sl) * lot_size
            max_risk = CAPITAL * 0.02
            lots = max(1, min(5, int(max_risk / max(risk_per_lot, 1))))  # cap at 5 lots
            capital_used = entry * lot_size * lots
            commission = COMMISSION_PER_LOT * lots  # FIX: commissions

            # FIX #4: Entry timing
            entry_zone = _calc_entry_zone(chain, spot, atm, side, strike_step, entry)

            trade = {
                "strike": f"{pick['strike']} {side}",
                "side": side,
                "entry": round(entry, 1),
                "stop_loss": sl,
                "sl_type": sl_type,
                "target1": t1,
                "target2": t2,
                "lots": lots,
                "lot_size": lot_size,
                "capital_used": round(capital_used, 0),
                "max_loss": round(risk_per_lot * lots, 0),
                "volume": pick["vol"],
                "oi": pick["oi"],
                "commission": round(commission, 0),
                "slippage_applied": f"{SLIPPAGE_PCT*100}%",
                "entry_zone": entry_zone,
            }

            _active_trade = {**trade, "entry_time": now.isoformat(), "status": "ACTIVE"}
            _last_signal_ts = now_ts
            _save_trade({**trade, "signal": signal, "reason": reason, "entry_time": now.isoformat(),
                         "votes": {"bull": bull, "bear": bear, "net": net}, "conviction": round(conviction, 1)})

            trade_tracker.open_trade(signal, trade, reason, conviction)

            try:
                asyncio.get_event_loop().call_soon(
                    lambda: asyncio.ensure_future(
                        telegram_alerts.send_buy_signal(signal, trade, reason,
                            {"bullish": bull, "bearish": bear}, conviction)))
            except Exception:
                pass
        else:
            signal = "WAIT"
            reason = "No suitable strike (premium < ₹10)"
            what_to_change.append("Wait for ATM/OTM premium ≥ ₹10")

    # ══════════════════════════════════════════
    #  STEP 6: Running trade monitor
    # ══════════════════════════════════════════
    position_monitor = None
    if _active_trade and _active_trade.get("status") == "ACTIVE" and chain:
        active_strike = int(_active_trade["strike"].split()[0])
        active_side = _active_trade["side"]
        active_entry = _active_trade["entry"]

        current_info = chain.get(active_strike, {}).get(active_side, {})
        current_ltp = current_info.get("last_price", 0) if current_info else 0
        pnl_pct = ((current_ltp - active_entry) / active_entry * 100) if active_entry > 0 else 0

        if current_ltp > 0:
            closed = trade_tracker.check_and_close(current_ltp)
            if closed:
                try:
                    asyncio.get_event_loop().call_soon(
                        lambda c=closed: asyncio.ensure_future(
                            telegram_alerts.send_exit_alert(c["exit_reason"],
                                f"{c['strike']} — ₹{c['entry']} → ₹{c['exit_price']}", c["exit_reason"], c["pnl_pct"])))
                except Exception:
                    pass
                if "SL" in closed["exit_reason"]:
                    _active_trade["status"] = "SL_HIT"

        nearby = []
        for offset in range(-4, 5):
            check_strike = active_strike + offset * strike_step
            info = chain.get(check_strike, {}).get(active_side, {})
            if info:
                oi_chg = info.get("oi_day_change", 0)
                nearby.append({"strike": int(check_strike), "oi_chg": oi_chg,
                               "ltp": info.get("last_price", 0), "is_active": offset == 0,
                               "action": "WRITING" if oi_chg > 5000 else "COVERING" if oi_chg < -5000 else "STABLE"})

        alerts = []
        for n in nearby:
            if n["is_active"]: continue
            if abs(n["strike"] - active_strike) <= strike_step * 2 and n["oi_chg"] > 50000:
                alerts.append({"type": "SL_HUNT_RISK", "severity": "HIGH",
                               "msg": f"Heavy OI at {n['strike']} (+{n['oi_chg']:,}) — SL hunt risk",
                               "action": f"Tighten SL to ₹{round(current_ltp * 0.92, 1)}"})

        if pnl_pct > 20:
            new_sl = round(active_entry * 1.05, 1)
            alerts.append({"type": "TRAIL_SL", "severity": "INFO",
                           "msg": f"+{pnl_pct:.0f}% profit. Trail SL → ₹{new_sl}",
                           "action": f"SL ₹{_active_trade['stop_loss']} → ₹{new_sl}"})

        active_oi_chg = current_info.get("oi_day_change", 0) if current_info else 0
        if active_oi_chg < -30000 and pnl_pct < 0:
            alerts.append({"type": "EXIT_WARNING", "severity": "CRITICAL",
                           "msg": f"OI unwinding ({active_oi_chg:,}) + loss ({pnl_pct:.0f}%)",
                           "action": "EXIT — OI against you"})

        if current_ltp > 0 and current_ltp <= _active_trade.get("stop_loss", 0):
            alerts.append({"type": "SL_HIT", "severity": "CRITICAL",
                           "msg": f"SL HIT — ₹{current_ltp} ≤ ₹{_active_trade['stop_loss']}",
                           "action": "EXIT NOW"})
            _active_trade["status"] = "SL_HIT"

        if current_ltp >= _active_trade.get("target1", 999999) and _active_trade.get("status") == "ACTIVE":
            alerts.append({"type": "T1_HIT", "severity": "INFO",
                           "msg": f"T1 HIT — ₹{current_ltp} ≥ ₹{_active_trade['target1']}",
                           "action": "Book 50%, hold rest for T2"})

        _position_alerts.extend(alerts)
        position_monitor = {
            "active_trade": _active_trade, "current_ltp": round(current_ltp, 1),
            "pnl_pct": round(pnl_pct, 1),
            "pnl_abs": round((current_ltp - active_entry) * lot_size * _active_trade.get("lots", 1), 0),
            "nearby_strikes": nearby, "alerts": alerts, "all_alerts": list(_position_alerts)[-10:],
        }

    # ══════════════════════════════════════════
    #  STEP 7: Reports
    # ══════════════════════════════════════════
    tracker_report = trade_tracker.get_daily_report()
    today_stats = {
        "total_trades": tracker_report.get("total_trades", 0),
        "wins": tracker_report.get("wins", 0),
        "losses": tracker_report.get("losses", 0),
        "win_rate": tracker_report.get("win_rate", 0),
        "total_pnl": tracker_report.get("total_pnl", 0),
        "avg_pnl_pct": tracker_report.get("avg_pnl_pct", 0),
        "best_trade": tracker_report.get("best_trade"),
        "worst_trade": tracker_report.get("worst_trade"),
        "max_drawdown": tracker_report.get("max_drawdown", 0),
        "trades": tracker_report.get("trades", [])[-5:],
    }

    return {
        "timestamp": now.isoformat(),
        "signal": signal,
        "direction": direction,
        "side": side,
        "reason": reason,
        "trade": trade,
        "entry_zone": entry_zone,
        "votes": {"bullish": bull, "bearish": bear, "net": net, "total": total_votes},
        "conviction": round(conviction, 1),
        "strength": round(strength, 2),
        "reasons_bull": reasons_bull[:5],
        "reasons_bear": reasons_bear[:5],
        # FIX #5: detailed wait reasons
        "wait_reasons": wait_reasons,
        "what_to_change": what_to_change,
        "gates": {
            "ivr": ivr_gate,
            "ivr_value": ivr_val,
            "gex": gex_gate,
            "gex_value": net_gex,
            "market": "OPEN" if market_active else "CLOSED",
            "regime": regime,
        },
        "position_monitor": position_monitor,
        "today_stats": today_stats,
        "market_intel": mi,
        "telegram_active": telegram_alerts.is_configured(),
        "paper_trade_active": trade_tracker.get_active() is not None,
        "capital": CAPITAL,
        "max_sl_pct": f"{MAX_SL_PCT * 100:.0f}%",
        "auto_tune": get_tune_report(),
    }
