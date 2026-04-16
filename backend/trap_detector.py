"""Trap Reversal Detector — Catch SL hunts before the real move.

Pattern we detect:
1. SHARP DROP: Premium drops 25%+ from recent peak (SL hunt)
2. CONSOLIDATION: Price stabilizes in tight range for 3+ minutes
3. OI UNWIND: Sellers quietly covering during consolidation
4. SMART MONEY: Buy % rises during consolidation (hidden accumulation)
5. VOLUME HOLD: Volume doesn't dry up — someone is buying the dip

When all 5 conditions met → TRAP REVERSAL signal with entry at consolidation level.
This catches the move at 120, not 180.

Data tracked per strike (rolling 60 cycles = ~5 minutes at 5s refresh):
- Price history (LTP every cycle)
- OI history (every cycle)
- Volume history (every cycle)
- Buy % history (every cycle)
"""

import time
from collections import deque
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

# ── Config ──
HISTORY_LENGTH = 120         # FIX #11: ~10 minutes (was 60 = 5 min, missed bigger patterns)
DROP_THRESHOLD = 0.25        # 25% drop from peak = trap
CONSOL_RANGE_PCT = 0.10      # consolidation = price range < 10%
CONSOL_MIN_CYCLES = 6        # minimum 6 cycles (~30 seconds) in consolidation
OI_UNWIND_MIN = -10000       # FIX #11: OI must decrease 10K+ (was 3K — too sensitive)
SMART_MONEY_BUY_PCT = 0.52   # buy % > 52% during consolidation = accumulation
MIN_PREMIUM = 5              # minimum ₹5 premium to consider

# ── History storage (module-level persistence across cycles) ──
_strike_history: dict[str, dict] = {}
# key: "{strike}_{side}" → {prices: deque, ois: deque, vols: deque, buy_pcts: deque, ts: deque}

_active_traps: dict[str, dict] = {}  # currently detected traps
_trap_signals: list[dict] = []  # generated signals


def _get_history(key: str) -> dict:
    if key not in _strike_history:
        _strike_history[key] = {
            "prices": deque(maxlen=HISTORY_LENGTH),
            "ois": deque(maxlen=HISTORY_LENGTH),
            "vols": deque(maxlen=HISTORY_LENGTH),
            "buy_pcts": deque(maxlen=HISTORY_LENGTH),
            "ts": deque(maxlen=HISTORY_LENGTH),
        }
    return _strike_history[key]


def update_and_detect(chain: dict, spot: float, atm: int, strike_step: int = 50) -> dict:
    """Called every cycle. Updates history and detects trap reversals.

    Returns dict with:
    - traps: list of detected trap reversal setups
    - tracking: number of strikes being tracked
    - active_traps: currently in consolidation phase (not yet triggered)
    """
    global _active_traps, _trap_signals

    now = datetime.now(IST)
    now_ts = time.time()
    h, m = now.hour, now.minute

    # Market hours check
    market_active = (h == 9 and m >= 15) or (10 <= h <= 14) or (h == 15 and m <= 30)
    if not market_active or not chain or spot <= 0:
        return {"traps": [], "active_traps": [], "tracking": 0, "timestamp": now.isoformat()}

    traps = []
    active_setups = []

    for strike in sorted(chain.keys()):
        dist = abs(strike - atm) / strike_step
        if dist > 5:  # only ±5 strikes from ATM
            continue

        for side_key in ("CE", "PE"):
            info = chain[strike].get(side_key)
            if not info:
                continue

            ltp = info.get("last_price", 0)
            oi = info.get("oi", 0)
            vol = info.get("volume", 0)
            buy_pct = info.get("buy_pct", 0.5)

            if ltp < MIN_PREMIUM:
                continue

            key = f"{int(strike)}_{side_key}"
            hist = _get_history(key)

            # Record current values
            hist["prices"].append(ltp)
            hist["ois"].append(oi)
            hist["vols"].append(vol)
            hist["buy_pcts"].append(buy_pct)
            hist["ts"].append(now_ts)

            # Need minimum history to detect
            if len(hist["prices"]) < 12:  # at least 1 minute of data
                continue

            prices = list(hist["prices"])
            ois = list(hist["ois"])
            buy_pcts = list(hist["buy_pcts"])

            # ══════════════════════════════════════════
            #  PHASE 1: DETECT SHARP DROP (SL Hunt)
            # ══════════════════════════════════════════
            peak_price = max(prices)
            peak_idx = prices.index(peak_price)
            current_price = prices[-1]

            # Drop must be from a recent peak (within last 40 cycles = ~3.5 min)
            if peak_idx < len(prices) - 80:  # FIX #11: extended to ~7 min (was 40 = 3.3 min)
                continue  # peak too old

            drop_pct = (peak_price - current_price) / peak_price if peak_price > 0 else 0

            if drop_pct < DROP_THRESHOLD:
                continue  # not enough drop

            # Find the bottom after the drop
            post_peak = prices[peak_idx:]
            if len(post_peak) < 3:
                continue
            bottom_price = min(post_peak)
            bottom_idx = peak_idx + post_peak.index(bottom_price)

            # ══════════════════════════════════════════
            #  PHASE 2: DETECT CONSOLIDATION
            # ══════════════════════════════════════════
            # After bottom, check if price is consolidating
            post_bottom = prices[bottom_idx:]
            if len(post_bottom) < CONSOL_MIN_CYCLES:
                # Drop happened but not enough time for consolidation yet
                # Track as ACTIVE TRAP (developing)
                active_setups.append({
                    "strike": int(strike),
                    "side": side_key,
                    "peak": round(peak_price, 1),
                    "bottom": round(bottom_price, 1),
                    "current": round(current_price, 1),
                    "drop_pct": round(drop_pct * 100, 1),
                    "phase": "DROPPING",
                    "detail": f"{int(strike)} {side_key}: Peak ₹{peak_price:.0f} → Bottom ₹{bottom_price:.0f} ({drop_pct*100:.0f}% drop). Waiting for consolidation...",
                    "cycles_since_bottom": len(post_bottom),
                })
                continue

            consol_high = max(post_bottom)
            consol_low = min(post_bottom)
            consol_range = (consol_high - consol_low) / consol_low if consol_low > 0 else 1

            is_consolidating = consol_range < CONSOL_RANGE_PCT

            if not is_consolidating:
                # Price still volatile after drop — no consolidation yet
                active_setups.append({
                    "strike": int(strike),
                    "side": side_key,
                    "peak": round(peak_price, 1),
                    "bottom": round(bottom_price, 1),
                    "current": round(current_price, 1),
                    "drop_pct": round(drop_pct * 100, 1),
                    "phase": "VOLATILE",
                    "detail": f"{int(strike)} {side_key}: Dropped {drop_pct*100:.0f}% but still volatile (range {consol_range*100:.0f}%). Not consolidating yet.",
                    "cycles_since_bottom": len(post_bottom),
                })
                continue

            # ══════════════════════════════════════════
            #  PHASE 3: CHECK OI UNWIND during consolidation
            # ══════════════════════════════════════════
            oi_at_bottom = ois[bottom_idx] if bottom_idx < len(ois) else ois[-1]
            oi_now = ois[-1]
            oi_change = oi_now - oi_at_bottom
            oi_unwinding = oi_change < OI_UNWIND_MIN  # OI decreased = sellers covering

            # ══════════════════════════════════════════
            #  PHASE 4: CHECK SMART MONEY (buy % during consolidation)
            # ══════════════════════════════════════════
            consol_buy_pcts = buy_pcts[bottom_idx:]
            avg_buy_pct = sum(consol_buy_pcts) / len(consol_buy_pcts) if consol_buy_pcts else 0.5
            smart_money = avg_buy_pct > SMART_MONEY_BUY_PCT

            # ══════════════════════════════════════════
            #  SCORE & SIGNAL
            # ══════════════════════════════════════════
            conditions = {
                "sharp_drop": True,  # already confirmed above
                "consolidation": is_consolidating,
                "oi_unwind": oi_unwinding,
                "smart_money": smart_money,
            }
            conditions_met = sum(1 for v in conditions.values() if v)

            # Need at least 3/4 conditions for signal
            if conditions_met >= 3:
                # TRAP REVERSAL detected!
                entry = round(current_price, 1)
                sl = round(bottom_price * 0.9, 1)  # SL below bottom
                t1 = round(peak_price * 0.9, 1)    # T1 = near peak
                t2 = round(peak_price * 1.2, 1)    # T2 = above peak

                trap = {
                    "strike": int(strike),
                    "side": side_key,
                    "signal": "TRAP REVERSAL",
                    "phase": "BUY ZONE",
                    "entry": entry,
                    "stop_loss": sl,
                    "target1": t1,
                    "target2": t2,
                    "peak": round(peak_price, 1),
                    "bottom": round(bottom_price, 1),
                    "drop_pct": round(drop_pct * 100, 1),
                    "consol_range_pct": round(consol_range * 100, 1),
                    "oi_change": oi_change,
                    "avg_buy_pct": round(avg_buy_pct * 100, 1),
                    "conditions": conditions,
                    "conditions_met": f"{conditions_met}/4",
                    "conviction": "HIGH" if conditions_met == 4 else "MODERATE",
                    "detail": (
                        f"SL HUNT detected at {int(strike)} {side_key}! "
                        f"Peak ₹{peak_price:.0f} → Dropped to ₹{bottom_price:.0f} ({drop_pct*100:.0f}% drop). "
                        f"Now consolidating at ₹{current_price:.0f} (range {consol_range*100:.0f}%). "
                        f"{'OI unwinding (sellers covering)' if oi_unwinding else 'OI stable'}. "
                        f"Buy side {avg_buy_pct*100:.0f}% {'= smart money accumulating' if smart_money else ''}. "
                        f"ENTRY NOW at ₹{current_price:.0f}, SL ₹{sl:.0f}, T1 ₹{t1:.0f}, T2 ₹{t2:.0f}."
                    ),
                    "timestamp": now.isoformat(),
                }
                traps.append(trap)
            else:
                # Partial conditions — track as developing
                active_setups.append({
                    "strike": int(strike),
                    "side": side_key,
                    "peak": round(peak_price, 1),
                    "bottom": round(bottom_price, 1),
                    "current": round(current_price, 1),
                    "drop_pct": round(drop_pct * 100, 1),
                    "phase": "CONSOLIDATING",
                    "conditions": conditions,
                    "conditions_met": f"{conditions_met}/4",
                    "oi_change": oi_change,
                    "avg_buy_pct": round(avg_buy_pct * 100, 1),
                    "detail": (
                        f"{int(strike)} {side_key}: Dropped {drop_pct*100:.0f}%, consolidating. "
                        f"{'OI unwinding ✓' if oi_unwinding else 'OI stable ✗'}, "
                        f"Buy% {avg_buy_pct*100:.0f}% {'✓' if smart_money else '✗'}. "
                        f"Need {4 - conditions_met} more condition(s)."
                    ),
                    "cycles_since_bottom": len(post_bottom),
                })

    return {
        "traps": traps,
        "active_traps": active_setups[:6],  # max 6 developing setups
        "tracking": len(_strike_history),
        "timestamp": now.isoformat(),
    }
