"""SNIPER — Phased Position Building Engine.

Think like smart money:
- DETECT early OI shifts before retail sees anything
- SCOUT with 1 lot on early signal (tight SL, low risk)
- BUILD position as confirmation arrives (+2 lots)
- FULL position when move is confirmed (trail SL, let it run)
- EXIT before reversal using OI wall breaks

Phases:
  SCAN    → watching, no position. Looking for early OI/dealer shifts.
  SCOUT   → 1 lot entered. Early signal, tight SL. Low risk probe.
  BUILD   → +2 lots added. Confirmation came. Move SL to breakeven.
  RIDE    → Full position. Trailing SL based on OI walls. Let it run.
  EXIT    → Booking profit or cutting loss. Reason logged.

Key principle: Enter EARLY at score 30-35, not late at 70-80.
When retail sees the trend, you're already +40% in profit.

Capital: ₹10,00,000 | NIFTY 75 | BANKNIFTY 30 | SENSEX 20
"""

import time
import json
import os
import math
from datetime import datetime, timezone, timedelta
from collections import deque

IST = timezone(timedelta(hours=5, minutes=30))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))

CAPITAL = 1000000
LOT_SIZES = {"NIFTY": 75, "BANKNIFTY": 30, "SENSEX": 20}

# Phase thresholds (NET votes = bull - bear)
SCOUT_NET = 3      # early signal — 1 lot probe
BUILD_NET = 5      # confirmation — add lots
RIDE_NET = 7       # full conviction — trail and ride
SCOUT_SCORE = 30   # minimum confluence score for scout
BUILD_SCORE = 45   # minimum for build
RIDE_SCORE = 60    # minimum for ride

# ── State persistence ──
_position: dict | None = None
_phase = "SCAN"
_scout_time: float = 0
_entries: list[dict] = []  # list of entries with lots and prices
_alerts: deque = deque(maxlen=30)
_phase_history: list[dict] = []  # track phase transitions


def _save_position():
    try:
        d = os.path.join(DATA_DIR, "sniper")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "active.json"), "w") as f:
            json.dump({"position": _position, "phase": _phase, "entries": _entries}, f, default=str)
    except Exception:
        pass


def _calc_net_direction(confluence: dict, seller: dict, dealer: dict,
                         vpin: dict, trap: dict) -> tuple[int, int, str, list[str]]:
    """Calculate net directional votes. Returns (bull, bear, direction, reasons)."""
    bull = 0
    bear = 0
    reasons = []

    # Confluence direction (weight 2)
    conf_dir = confluence.get("direction", "NEUTRAL")
    conf_score = confluence.get("score", 0)
    if conf_dir == "BULLISH" and conf_score > 25:
        bull += 2
        reasons.append(f"Confluence {conf_score:.0f} BULLISH")
    elif conf_dir == "BEARISH" and conf_score > 25:
        bear += 2
        reasons.append(f"Confluence {conf_score:.0f} BEARISH")

    # Seller footprint (weight 4)
    for sig in seller.get("signals", []):
        s = sig.get("signal", "")
        if "BUY CE" in s:
            bull += 4
            reasons.append(f"Seller: {sig.get('reason', '')[:50]}")
        elif "BUY PE" in s:
            bear += 4
            reasons.append(f"Seller: {sig.get('reason', '')[:50]}")
        elif "AVOID CE" in s:
            bear += 2

    # Dealer (weight 5)
    for sig in dealer.get("signals", []):
        s = sig.get("signal", "")
        w = 5 if sig.get("source") == "DEALER DELTA FLIP" else 4
        if "CE" in s and "AVOID" not in s:
            bull += w
            reasons.append(f"Dealer: {sig.get('reason', '')[:50]}")
        elif "PE" in s:
            bear += w
            reasons.append(f"Dealer: {sig.get('reason', '')[:50]}")

    # VPIN (weight 2)
    ce_vpin = vpin.get("ce_vpin", 0)
    pe_vpin = vpin.get("pe_vpin", 0)
    if ce_vpin > pe_vpin + 0.1:
        bull += 2
        reasons.append("VPIN: CE side toxic")
    elif pe_vpin > ce_vpin + 0.1:
        bear += 2
        reasons.append("VPIN: PE side toxic")

    # Trap (weight 3)
    for t in trap.get("traps", []):
        if t.get("side") == "CE":
            bull += 3
            reasons.append(f"Trap reversal: {t['strike']} CE")
        elif t.get("side") == "PE":
            bear += 3
            reasons.append(f"Trap reversal: {t['strike']} PE")

    direction = "BULLISH" if bull > bear else "BEARISH" if bear > bull else "NEUTRAL"
    return bull, bear, direction, reasons


def _find_oi_wall(chain: dict, spot: float, atm: int, side: str, direction: str, step: int) -> float:
    """Find nearest OI wall for dynamic SL. Returns price level."""
    if not chain:
        return 0

    if direction == "BULLISH":
        # For CE buy, SL = PE OI wall below spot (support)
        walls = []
        for strike in sorted(chain.keys()):
            if strike >= atm:
                continue
            pe = chain[strike].get("PE", {})
            oi = pe.get("oi", 0)
            if oi > 50000:
                walls.append((strike, oi))
        if walls:
            # Nearest significant wall below ATM
            best = max(walls, key=lambda w: w[1])
            # CE premium at that spot level (rough estimate)
            ce_at_wall = chain.get(atm, {}).get("CE", {})
            if ce_at_wall:
                current = ce_at_wall.get("last_price", 0)
                drop_pct = (spot - best[0]) / spot
                sl_price = current * (1 - drop_pct * 3)  # premium drops ~3x the underlying %
                return max(round(sl_price, 1), current * 0.70)  # floor at 30% loss
    else:
        # For PE buy, SL = CE OI wall above spot (resistance)
        walls = []
        for strike in sorted(chain.keys()):
            if strike <= atm:
                continue
            ce = chain[strike].get("CE", {})
            oi = ce.get("oi", 0)
            if oi > 50000:
                walls.append((strike, oi))
        if walls:
            best = max(walls, key=lambda w: w[1])
            pe_at_wall = chain.get(atm, {}).get("PE", {})
            if pe_at_wall:
                current = pe_at_wall.get("last_price", 0)
                rise_pct = (best[0] - spot) / spot
                sl_price = current * (1 - rise_pct * 3)
                return max(round(sl_price, 1), current * 0.70)

    return 0  # no wall found, use fallback


def _pick_strike(chain: dict, atm: int, side: str, step: int) -> dict | None:
    """Pick entry strike: ATM or 1 OTM, premium ≥ ₹10."""
    for offset in [0, 1, 2]:
        strike = atm + (offset * step if side == "CE" else -offset * step)
        info = chain.get(strike, {}).get(side, {})
        if info and info.get("last_price", 0) >= 10:
            return {"strike": int(strike), "side": side, "ltp": info["last_price"],
                    "vol": info.get("volume", 0), "oi": info.get("oi", 0),
                    "iv": info.get("iv", 0)}
    return None


def analyze(confluence: dict, detectors: dict, seller: dict, vpin: dict,
            trap: dict, dealer: dict, chain: dict, spot: float, atm: int,
            index_id: str = "NIFTY", strike_step: int = 50,
            market_intel: dict | None = None) -> dict:
    """SNIPER main function. Called every cycle. Manages phased positions."""
    global _position, _phase, _scout_time, _entries

    now = datetime.now(IST)
    now_ts = time.time()
    h, m = now.hour, now.minute
    lot_size = LOT_SIZES.get(index_id, 75)
    mi = market_intel or {}

    # Market hours
    market_active = (h == 9 and m >= 18) or (10 <= h <= 14) or (h == 15 and m < 20)

    # Direction
    bull, bear, direction, reasons = _calc_net_direction(confluence, seller, dealer, vpin, trap)
    net = bull - bear if direction == "BULLISH" else bear - bull if direction == "BEARISH" else 0
    net_raw = bull - bear  # positive = bullish
    conf_score = confluence.get("score", 0)
    side = "CE" if direction == "BULLISH" else "PE"

    # Regime
    regime = mi.get("regime", {}).get("regime", "UNKNOWN")
    tradeability = mi.get("tradeability", {}).get("verdict", "GO")

    # ══════════════════════════════════════════
    #  ACTIVE POSITION MANAGEMENT
    # ══════════════════════════════════════════
    if _position and _phase in ("SCOUT", "BUILD", "RIDE"):
        pos_strike = int(_position["strike"].split()[0])
        pos_side = _position["side"]
        current_info = chain.get(pos_strike, {}).get(pos_side, {})
        current_ltp = current_info.get("last_price", 0) if current_info else 0

        if current_ltp <= 0:
            return _build_output(now, bull, bear, direction, net_raw, reasons, conf_score, regime, tradeability)

        avg_entry = _position["avg_entry"]
        total_lots = _position["total_lots"]
        pnl_pct = (current_ltp - avg_entry) / avg_entry * 100

        # Check SL
        if current_ltp <= _position.get("stop_loss", 0):
            _alerts.append({"time": now.strftime("%H:%M:%S"), "type": "SL_HIT",
                            "msg": f"SL HIT at ₹{current_ltp}. Exiting {total_lots} lots. P&L: {pnl_pct:+.1f}%"})
            _close_position("SL HIT", current_ltp, pnl_pct)
            _phase = "SCAN"
        # Check targets
        elif pnl_pct >= 60 and _phase == "RIDE":
            _alerts.append({"time": now.strftime("%H:%M:%S"), "type": "T2_HIT",
                            "msg": f"TARGET 2 HIT (+{pnl_pct:.0f}%). Book full profit."})
            _close_position("T2 HIT", current_ltp, pnl_pct)
            _phase = "SCAN"
        elif pnl_pct >= 30 and _phase in ("BUILD", "RIDE"):
            # Trail SL to breakeven + 5%
            new_sl = round(avg_entry * 1.05, 1)
            if new_sl > _position.get("stop_loss", 0):
                _position["stop_loss"] = new_sl
                _alerts.append({"time": now.strftime("%H:%M:%S"), "type": "TRAIL_SL",
                                "msg": f"Trailing SL to ₹{new_sl} (locking +5% profit)"})

        # Time stop: 30 min in SCOUT with no progress
        elif _phase == "SCOUT" and now_ts - _scout_time > 1800 and abs(pnl_pct) < 5:
            _alerts.append({"time": now.strftime("%H:%M:%S"), "type": "TIME_STOP",
                            "msg": f"30 min in SCOUT, no movement. Exiting 1 lot."})
            _close_position("TIME STOP", current_ltp, pnl_pct)
            _phase = "SCAN"

        # OI wall break warning
        for offset in range(-4, 5):
            check_strike = pos_strike + offset * strike_step
            oi_info = chain.get(check_strike, {}).get(pos_side, {})
            oi_chg = oi_info.get("oi_day_change", 0) if oi_info else 0
            if offset != 0 and abs(offset) <= 2 and oi_chg > 80000:
                _alerts.append({"time": now.strftime("%H:%M:%S"), "type": "OI_WARNING",
                                "msg": f"Heavy OI buildup at {check_strike} ({oi_chg:+,}) — potential resistance"})

        # Phase upgrade: SCOUT → BUILD (FIX #2: strict conditions, no averaging down)
        if _phase == "SCOUT" and net >= BUILD_NET and conf_score >= BUILD_SCORE:
            if pnl_pct > 0 and direction == _position.get("direction"):  # MUST be in profit AND same direction
                add_lots = 2
                _position["total_lots"] += add_lots
                new_avg = (avg_entry * total_lots + current_ltp * add_lots) / (total_lots + add_lots)
                _position["avg_entry"] = round(new_avg, 1)
                _entries.append({"phase": "BUILD", "price": current_ltp, "lots": add_lots, "time": now.isoformat()})
                # Move SL to breakeven
                _position["stop_loss"] = round(new_avg * 0.92, 1)
                _phase = "BUILD"
                _alerts.append({"time": now.strftime("%H:%M:%S"), "type": "BUILD",
                                "msg": f"PHASE UP → BUILD: Added {add_lots} lots at ₹{current_ltp}. Total {_position['total_lots']} lots. SL → ₹{_position['stop_loss']}"})

        # Phase upgrade: BUILD → RIDE
        if _phase == "BUILD" and net >= RIDE_NET and conf_score >= RIDE_SCORE:
            _phase = "RIDE"
            # Dynamic SL from OI wall
            oi_sl = _find_oi_wall(chain, spot, atm, side, direction, strike_step)
            if oi_sl > 0 and oi_sl > _position.get("stop_loss", 0):
                _position["stop_loss"] = oi_sl
            _alerts.append({"time": now.strftime("%H:%M:%S"), "type": "RIDE",
                            "msg": f"PHASE UP → RIDE: Full conviction. Trailing SL at ₹{_position['stop_loss']}. Let it run."})

        # Update position with current data
        _position["current_ltp"] = round(current_ltp, 1)
        _position["pnl_pct"] = round(pnl_pct, 1)
        _position["pnl_abs"] = round((current_ltp - avg_entry) * lot_size * total_lots, 0)

    # ══════════════════════════════════════════
    #  NEW POSITION: SCAN → SCOUT
    # ══════════════════════════════════════════
    if _phase == "SCAN" and market_active and tradeability != "AVOID":
        if direction != "NEUTRAL" and net >= SCOUT_NET and conf_score >= SCOUT_SCORE:
            pick = _pick_strike(chain, atm, side, strike_step)
            if pick:
                entry = pick["ltp"]
                # Dynamic SL from OI wall or fallback 15%
                oi_sl = _find_oi_wall(chain, spot, atm, side, direction, strike_step)
                sl = oi_sl if oi_sl > 0 else round(entry * 0.85, 1)

                _position = {
                    "strike": f"{pick['strike']} {side}",
                    "side": side,
                    "direction": direction,
                    "avg_entry": round(entry, 1),
                    "current_ltp": round(entry, 1),
                    "stop_loss": sl,
                    "target1": round(entry * 1.30, 1),
                    "target2": round(entry * 1.60, 1),
                    "total_lots": 1,
                    "lot_size": lot_size,
                    "pnl_pct": 0,
                    "pnl_abs": 0,
                    "entry_time": now.isoformat(),
                    "capital_used": round(entry * lot_size * 1, 0),
                    "iv": pick.get("iv", 0),
                }
                _entries = [{"phase": "SCOUT", "price": entry, "lots": 1, "time": now.isoformat()}]
                _phase = "SCOUT"
                _scout_time = now_ts
                _save_position()
                _alerts.append({"time": now.strftime("%H:%M:%S"), "type": "SCOUT",
                                "msg": f"SCOUT ENTRY: 1 lot {pick['strike']} {side} at ₹{entry}. SL ₹{sl}. Net votes: {net_raw:+d} ({direction})"})

    return _build_output(now, bull, bear, direction, net_raw, reasons, conf_score, regime, tradeability)


def _close_position(reason: str, exit_price: float, pnl_pct: float):
    global _position, _entries
    if _position:
        _position["exit_reason"] = reason
        _position["exit_price"] = exit_price
        _position["exit_pnl"] = round(pnl_pct, 1)
        _position["exit_time"] = datetime.now(IST).isoformat()
        _phase_history.append({**_position, "entries": _entries.copy()})
        # Save to disk
        try:
            d = os.path.join(DATA_DIR, "sniper")
            os.makedirs(d, exist_ok=True)
            date = datetime.now(IST).strftime("%Y-%m-%d")
            path = os.path.join(d, f"history_{date}.json")
            existing = []
            if os.path.exists(path):
                with open(path) as f:
                    existing = json.load(f)
            existing.append({**_position, "entries": _entries})
            with open(path, "w") as f:
                json.dump(existing, f, default=str)
        except Exception:
            pass
    _position = None
    _entries = []


def _build_output(now, bull, bear, direction, net_raw, reasons, conf_score, regime, tradeability) -> dict:
    return {
        "timestamp": now.isoformat(),
        "phase": _phase,
        "position": _position,
        "entries": _entries,
        "direction": direction,
        "net_votes": net_raw,
        "bull_votes": bull,
        "bear_votes": bear,
        "conf_score": round(conf_score, 1),
        "reasons": reasons[:5],
        "regime": regime,
        "tradeability": tradeability,
        "alerts": list(_alerts)[-10:],
        "phase_thresholds": {
            "scout": f"Net ≥{SCOUT_NET}, Score ≥{SCOUT_SCORE}",
            "build": f"Net ≥{BUILD_NET}, Score ≥{BUILD_SCORE}",
            "ride": f"Net ≥{RIDE_NET}, Score ≥{RIDE_SCORE}",
        },
        "closed_trades": _phase_history[-5:],
    }
