"""Command Center — ONE brain, ONE signal, ONE voice.

Merges ALL data sources into a single actionable trade signal.
No conflicting signals. Quality over quantity.

Sources merged:
- 16 detectors (confluence score + direction)
- Seller Footprint (OI walls, covering, writing)
- VPIN (flow toxicity, CE vs PE bias)
- Trap Detector (SL hunt reversal patterns)
- Dealer Positions (panic velocity, gamma squeeze, delta flip)
- Bob gates (IVR, GEX, momentum)

Output: ONE trade with entry/exit/SL + running trade monitor + auto-save

Capital: ₹10,00,000
Max SL: 15% of premium
Lot sizes: NIFTY=75, BANKNIFTY=30, SENSEX=20
"""

import time
import json
import os
from datetime import datetime, timezone, timedelta
from collections import deque

IST = timezone(timedelta(hours=5, minutes=30))

CAPITAL = 1000000
MAX_SL_PCT = 0.15  # 15% max stoploss
LOT_SIZES = {"NIFTY": 75, "BANKNIFTY": 30, "SENSEX": 20}
T1_MULT = 1.30  # +30% target 1
T2_MULT = 1.60  # +60% target 2

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))

# ── Running trade state ──
_active_trade: dict | None = None
_trade_history: list[dict] = []
_position_alerts: deque = deque(maxlen=20)
_last_signal_ts: float = 0
SIGNAL_COOLDOWN = 600  # 10 min between new signals


def _save_trade(trade: dict):
    """Auto-save trade to disk."""
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
    except Exception as e:
        print(f"[CMD] Save error: {e}")


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
    """Pick best strike: ATM or 1 OTM, premium ≥ ₹10."""
    candidates = []
    for strike in sorted(chain.keys()):
        info = chain[strike].get(side)
        if not info or info.get("last_price", 0) < 10:
            continue
        ltp = info["last_price"]
        # Only ATM and OTM
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
    """Generate ONE unified signal from ALL sources + market intelligence."""
    global _active_trade, _last_signal_ts

    now = datetime.now(IST)
    now_ts = time.time()
    h, m = now.hour, now.minute
    lot_size = LOT_SIZES.get(index_id, 75)

    # Market hours
    market_active = (h == 9 and m >= 18) or (10 <= h <= 14) or (h == 15 and m < 20)

    # ══════════════════════════════════════════
    #  STEP 1: Collect votes from all sources
    # ══════════════════════════════════════════
    bullish_votes = 0
    bearish_votes = 0
    reasons_bull = []
    reasons_bear = []
    conviction_total = 0

    # A) Confluence direction (weight: 3)
    conf_dir = confluence.get("direction", "NEUTRAL")
    conf_score = confluence.get("score", 0)
    if conf_dir == "BULLISH" and conf_score > 40:
        bullish_votes += 3
        reasons_bull.append(f"Confluence {conf_score:.0f}/100 BULLISH")
        conviction_total += min(3, conf_score / 30)
    elif conf_dir == "BEARISH" and conf_score > 40:
        bearish_votes += 3
        reasons_bear.append(f"Confluence {conf_score:.0f}/100 BEARISH")
        conviction_total += min(3, conf_score / 30)

    # B) Seller Footprint (weight: 4 — most important for buyer)
    seller_signals = seller.get("signals", [])
    for sig in seller_signals:
        if sig.get("signal", "").startswith("BUY CE"):
            bullish_votes += 4
            reasons_bull.append(f"Sellers: {sig.get('reason', '')[:60]}")
            conviction_total += 3 if sig.get("conviction") == "HIGH" else 2
        elif sig.get("signal", "").startswith("BUY PE"):
            bearish_votes += 4
            reasons_bear.append(f"Sellers: {sig.get('reason', '')[:60]}")
            conviction_total += 3 if sig.get("conviction") == "HIGH" else 2
        elif "AVOID CE" in sig.get("signal", ""):
            bearish_votes += 2
            reasons_bear.append("Heavy call writing — upside capped")

    # C) VPIN flow bias (weight: 2)
    ce_vpin = vpin.get("ce_vpin", 0)
    pe_vpin = vpin.get("pe_vpin", 0)
    if ce_vpin > pe_vpin + 0.1:
        bullish_votes += 2
        reasons_bull.append(f"VPIN: CE side toxic ({ce_vpin:.0%}) — call sellers stressed")
    elif pe_vpin > ce_vpin + 0.1:
        bearish_votes += 2
        reasons_bear.append(f"VPIN: PE side toxic ({pe_vpin:.0%}) — put sellers stressed")

    # D) Dealer Positions (weight: 5 — institutional level)
    dealer_signals = dealer.get("signals", [])
    for sig in dealer_signals:
        weight = 5 if sig.get("source") == "DEALER DELTA FLIP" else 4 if sig.get("source") == "DEALER PANIC" else 3
        if "CE" in sig.get("signal", ""):
            bullish_votes += weight
            reasons_bull.append(f"Dealer: {sig.get('reason', '')[:60]}")
            conviction_total += 4 if sig.get("conviction") == "MAXIMUM" else 3
        elif "PE" in sig.get("signal", ""):
            bearish_votes += weight
            reasons_bear.append(f"Dealer: {sig.get('reason', '')[:60]}")
            conviction_total += 4 if sig.get("conviction") == "MAXIMUM" else 3

    # E) Trap Detector (weight: 3)
    for t in trap.get("traps", []):
        if t.get("side") == "CE":
            bullish_votes += 3
            reasons_bull.append(f"Trap: SL hunt at {t['strike']} CE, entry ₹{t.get('entry', 0)}")
            conviction_total += 2
        elif t.get("side") == "PE":
            bearish_votes += 3
            reasons_bear.append(f"Trap: SL hunt at {t['strike']} PE, entry ₹{t.get('entry', 0)}")
            conviction_total += 2

    # F) Bob gates as filter (not votes — blockers)
    bob_blocked = bob.get("signal") == "WAIT" and "GATE" in bob.get("reason", "")
    ivr_status = bob.get("gates", {}).get("ivr", {}).get("status", "GREEN")
    gex_status = bob.get("gates", {}).get("gex", {}).get("status", "GREEN")

    # G) Market Regime (blocker for range)
    mi = market_intel or {}
    regime = mi.get("regime", {}).get("regime", "UNKNOWN")
    tradeability = mi.get("tradeability", {}).get("score", 100)
    trade_verdict = mi.get("tradeability", {}).get("verdict", "GO")

    # ══════════════════════════════════════════
    #  STEP 2: Determine direction
    # ══════════════════════════════════════════
    total_votes = bullish_votes + bearish_votes
    if total_votes == 0:
        direction = "NEUTRAL"
        strength = 0
    elif bullish_votes > bearish_votes:
        direction = "BULLISH"
        strength = bullish_votes / max(total_votes, 1)
    else:
        direction = "BEARISH"
        strength = bearish_votes / max(total_votes, 1)

    side = "CE" if direction == "BULLISH" else "PE"
    reasons = reasons_bull if direction == "BULLISH" else reasons_bear
    winning_votes = bullish_votes if direction == "BULLISH" else bearish_votes

    # ══════════════════════════════════════════
    #  STEP 3: Signal decision
    # ══════════════════════════════════════════
    signal = "WAIT"
    reason = "Insufficient confluence"

    if not market_active:
        signal = "MARKET CLOSED"
        reason = "No trading outside 9:18-15:20 IST"
    elif trade_verdict == "AVOID":
        signal = "WAIT"
        reason = f"Market not tradeable ({regime}) — " + "; ".join(mi.get("tradeability", {}).get("reasons_against", [])[:2])
    elif ivr_status == "RED":
        signal = "WAIT"
        reason = "IVR too high — premium expensive, IV crush risk"
    elif direction == "NEUTRAL" or winning_votes < 5:
        signal = "WAIT"
        reason = f"Not enough votes — Bull {bullish_votes} vs Bear {bearish_votes}. Need 5+ on one side."
    elif winning_votes >= 10 and conviction_total >= 8:
        signal = "STRONG BUY"
        reason = " | ".join(reasons[:3])
    elif winning_votes >= 7 and conviction_total >= 5:
        signal = "BUY"
        reason = " | ".join(reasons[:3])
    elif winning_votes >= 5:
        signal = "WATCHLIST"
        reason = f"Building — {winning_votes} votes. " + (reasons[0] if reasons else "")

    # Cooldown check
    if signal in ("BUY", "STRONG BUY"):
        if now_ts - _last_signal_ts < SIGNAL_COOLDOWN and _active_trade:
            if _active_trade.get("side") != side:
                signal = "WAIT"
                reason = f"Cooldown — active {_active_trade['side']} trade. Wait {int(SIGNAL_COOLDOWN - (now_ts - _last_signal_ts))}s."

    # ══════════════════════════════════════════
    #  STEP 4: Pick strike + position sizing
    # ══════════════════════════════════════════
    trade = None
    if signal in ("BUY", "STRONG BUY") and chain:
        pick = _pick_best_strike(chain, spot, atm, side, strike_step)
        if pick:
            entry = pick["ltp"]
            sl = round(entry * (1 - MAX_SL_PCT), 1)
            t1 = round(entry * T1_MULT, 1)
            t2 = round(entry * T2_MULT, 1)
            risk_per_lot = (entry - sl) * lot_size
            max_risk = CAPITAL * 0.02  # 2% per trade
            lots = max(1, int(max_risk / max(risk_per_lot, 1)))
            capital_used = entry * lot_size * lots

            trade = {
                "strike": f"{pick['strike']} {side}",
                "side": side,
                "entry": round(entry, 1),
                "stop_loss": sl,
                "target1": t1,
                "target2": t2,
                "lots": lots,
                "lot_size": lot_size,
                "capital_used": round(capital_used, 0),
                "max_loss": round(risk_per_lot * lots, 0),
                "volume": pick["vol"],
                "oi": pick["oi"],
            }

            _active_trade = {**trade, "entry_time": now.isoformat(), "status": "ACTIVE"}
            _last_signal_ts = now_ts
            _save_trade({**trade, "signal": signal, "reason": reason, "entry_time": now.isoformat(),
                         "votes": {"bull": bullish_votes, "bear": bearish_votes},
                         "conviction": round(conviction_total, 1)})
        else:
            signal = "WAIT"
            reason = "No suitable strike found (premium < ₹10 or no OTM available)"

    # ══════════════════════════════════════════
    #  STEP 5: Running trade monitor (±4 strikes OI)
    # ══════════════════════════════════════════
    position_monitor = None
    if _active_trade and _active_trade.get("status") == "ACTIVE" and chain:
        active_strike = int(_active_trade["strike"].split()[0])
        active_side = _active_trade["side"]
        active_entry = _active_trade["entry"]

        # Get current LTP of active strike
        current_info = chain.get(active_strike, {}).get(active_side, {})
        current_ltp = current_info.get("last_price", 0) if current_info else 0
        pnl_pct = ((current_ltp - active_entry) / active_entry * 100) if active_entry > 0 else 0

        # Monitor ±4 strikes
        nearby = []
        for offset in range(-4, 5):
            check_strike = active_strike + offset * strike_step
            info = chain.get(check_strike, {}).get(active_side, {})
            if info:
                oi_chg = info.get("oi_day_change", 0)
                nearby.append({
                    "strike": int(check_strike),
                    "oi_chg": oi_chg,
                    "ltp": info.get("last_price", 0),
                    "is_active": offset == 0,
                    "action": "WRITING" if oi_chg > 5000 else "COVERING" if oi_chg < -5000 else "STABLE",
                })

        # Detect threats to position
        alerts = []

        # SL hunt warning: OI building at adjacent strikes against our position
        for n in nearby:
            if n["is_active"]: continue
            if abs(n["strike"] - active_strike) <= strike_step * 2:
                if n["oi_chg"] > 50000:
                    alerts.append({
                        "type": "SL_HUNT_RISK",
                        "msg": f"Heavy OI building at {n['strike']} (+{n['oi_chg']:,}) — sellers positioning. SL hunt possible.",
                        "action": f"Consider tightening SL from ₹{_active_trade['stop_loss']} to ₹{round(current_ltp * 0.92, 1)}",
                        "severity": "HIGH",
                    })

        # Profit protection
        if pnl_pct > 20:
            new_sl = round(active_entry * 1.05, 1)  # trail SL to +5% profit
            alerts.append({
                "type": "TRAIL_SL",
                "msg": f"Position +{pnl_pct:.0f}% in profit. Trail SL to ₹{new_sl} (lock +5% profit).",
                "action": f"Move SL from ₹{_active_trade['stop_loss']} → ₹{new_sl}",
                "severity": "INFO",
            })

        # OI unwinding at our strike = against us
        active_oi_chg = current_info.get("oi_day_change", 0) if current_info else 0
        if active_oi_chg < -30000 and pnl_pct < 0:
            alerts.append({
                "type": "EXIT_WARNING",
                "msg": f"OI unwinding at your strike ({active_oi_chg:,}) and position in loss ({pnl_pct:.0f}%). Consider exiting.",
                "action": "EXIT at market — OI moving against you",
                "severity": "CRITICAL",
            })

        # Auto-close check
        if current_ltp > 0 and current_ltp <= _active_trade.get("stop_loss", 0):
            alerts.append({
                "type": "SL_HIT",
                "msg": f"STOP LOSS HIT — LTP ₹{current_ltp} ≤ SL ₹{_active_trade['stop_loss']}. EXIT NOW.",
                "action": "EXIT IMMEDIATELY",
                "severity": "CRITICAL",
            })
            _active_trade["status"] = "SL_HIT"

        if current_ltp >= _active_trade.get("target1", 999999) and _active_trade.get("status") == "ACTIVE":
            alerts.append({
                "type": "T1_HIT",
                "msg": f"TARGET 1 HIT — LTP ₹{current_ltp} ≥ T1 ₹{_active_trade['target1']}. Book 50% profit.",
                "action": "SELL 50% — hold rest for T2",
                "severity": "INFO",
            })

        _position_alerts.extend(alerts)

        position_monitor = {
            "active_trade": _active_trade,
            "current_ltp": round(current_ltp, 1),
            "pnl_pct": round(pnl_pct, 1),
            "pnl_abs": round((current_ltp - active_entry) * lot_size * _active_trade.get("lots", 1), 0),
            "nearby_strikes": nearby,
            "alerts": alerts,
            "all_alerts": list(_position_alerts)[-10:],
        }

    # ══════════════════════════════════════════
    #  STEP 6: Reports
    # ══════════════════════════════════════════
    today_trades = _load_today_trades()
    today_stats = {
        "total_trades": len(today_trades),
        "signals": [t.get("signal", "") for t in today_trades[-5:]],
    }

    return {
        "timestamp": now.isoformat(),
        "signal": signal,
        "direction": direction,
        "side": side,
        "reason": reason,
        "trade": trade,
        "votes": {"bullish": bullish_votes, "bearish": bearish_votes, "total": total_votes},
        "conviction": round(conviction_total, 1),
        "strength": round(strength, 2),
        "reasons_bull": reasons_bull[:5],
        "reasons_bear": reasons_bear[:5],
        "gates": {
            "ivr": ivr_status,
            "gex": gex_status,
            "market": "OPEN" if market_active else "CLOSED",
        },
        "position_monitor": position_monitor,
        "today_stats": today_stats,
        "market_intel": mi,
        "capital": CAPITAL,
        "max_sl_pct": f"{MAX_SL_PCT * 100:.0f}%",
    }
