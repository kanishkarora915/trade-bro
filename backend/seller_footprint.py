"""Seller Footprint Engine v2 — Real-time OI tracking for option BUYERS.

Tracks every OI change across all strikes, builds cumulative seller position,
and generates BUY CE / BUY PE signals with entry/exit/SL.

Core:
- Track CE sellers (call writers) and PE sellers (put writers) separately
- Every OI add = seller entering, every OI unwind = seller exiting
- Cumulative sum → where are sellers building walls? where are they running?
- Conclusion: if sellers are running from calls → BUY CE (price will go up)
              if sellers are running from puts → BUY PE (price will go down)
              if sellers are writing heavily → AVOID (range-bound)

Flash Alerts:
- Sudden OI spike/drop mid-trade → EXIT ALERT with reason
"""

from datetime import datetime, timezone, timedelta
from collections import deque

IST = timezone(timedelta(hours=5, minutes=30))

# ── OI change thresholds ──
SIGNIFICANT_OI_CHG = 5000       # minimum OI change to track
HEAVY_OI_CHG = 50000            # heavy seller activity
MASSIVE_OI_CHG = 100000         # massive — flash alert
FLASH_ALERT_THRESHOLD = 80000   # sudden change triggers flash alert

# ── Persistence for tracking changes between cycles ──
_prev_chain_oi: dict = {}  # {strike_side: oi} — previous cycle's OI
_cumulative_ce_seller: dict = {}  # {strike: cumulative_oi_added_by_sellers}
_cumulative_pe_seller: dict = {}
_flash_alerts: deque = deque(maxlen=20)
_active_trade: dict | None = None  # currently active trade for flash monitoring


def _classify(oi_chg: float, price_chg: float) -> str:
    """OI + Price = seller action."""
    if oi_chg > 0 and price_chg <= 0:
        return "SELLER_WRITING"    # seller entering (writing options)
    if oi_chg < 0 and price_chg >= 0:
        return "SELLER_COVERING"   # seller exiting (covering shorts)
    if oi_chg > 0 and price_chg > 0:
        return "BUYER_ENTERING"    # buyer building longs
    if oi_chg < 0 and price_chg < 0:
        return "BUYER_EXITING"     # buyer unwinding longs
    return "NEUTRAL"


def analyze(chain: dict, spot: float, atm: int, strike_step: int = 50) -> dict:
    """Full seller footprint analysis with buy signals and flash alerts."""
    global _prev_chain_oi, _cumulative_ce_seller, _cumulative_pe_seller

    now = datetime.now(IST)
    h, m = now.hour, now.minute

    if not chain or spot <= 0:
        return _empty()

    strikes = sorted(chain.keys())

    # ══════════════════════════════════════════
    #  STEP 1: Track every OI change per strike
    # ══════════════════════════════════════════
    ce_activity = []  # all CE strikes with OI changes
    pe_activity = []  # all PE strikes with OI changes

    # Cumulative totals this cycle
    total_ce_oi_added = 0    # sellers writing calls
    total_ce_oi_removed = 0  # sellers covering calls
    total_pe_oi_added = 0    # sellers writing puts
    total_pe_oi_removed = 0  # sellers covering puts

    # Per-strike tracking
    ce_wall_strikes = []  # where CE sellers are building walls (resistance)
    pe_wall_strikes = []  # where PE sellers are building walls (support)
    ce_cover_strikes = [] # where CE sellers are running
    pe_cover_strikes = [] # where PE sellers are running

    for strike in strikes:
        dist = abs(strike - atm) / strike_step
        if dist > 10:
            continue

        sides = chain[strike]
        for side_key in ("CE", "PE"):
            info = sides.get(side_key)
            if not info:
                continue

            oi = info.get("oi", 0)
            oi_chg = info.get("oi_day_change", 0)
            ltp = info.get("last_price", 0)
            vol = info.get("volume", 0)
            net_chg = info.get("net_change", 0)
            buy_pct = info.get("buy_pct", 0.5)
            sell_pct = 1 - buy_pct

            # Classify seller action
            action = _classify(oi_chg, net_chg)

            # Track cycle-to-cycle delta (real-time micro changes)
            cache_key = f"{int(strike)}_{side_key}"
            prev_oi = _prev_chain_oi.get(cache_key, oi)
            micro_delta = oi - prev_oi  # change since last cycle (5 sec)
            _prev_chain_oi[cache_key] = oi

            # Update cumulative seller position
            if side_key == "CE":
                if oi_chg > SIGNIFICANT_OI_CHG:
                    total_ce_oi_added += oi_chg
                    _cumulative_ce_seller[int(strike)] = _cumulative_ce_seller.get(int(strike), 0) + max(0, micro_delta)
                elif oi_chg < -SIGNIFICANT_OI_CHG:
                    total_ce_oi_removed += abs(oi_chg)
            else:
                if oi_chg > SIGNIFICANT_OI_CHG:
                    total_pe_oi_added += oi_chg
                    _cumulative_pe_seller[int(strike)] = _cumulative_pe_seller.get(int(strike), 0) + max(0, micro_delta)
                elif oi_chg < -SIGNIFICANT_OI_CHG:
                    total_pe_oi_removed += abs(oi_chg)

            if abs(oi_chg) < SIGNIFICANT_OI_CHG:
                continue

            entry = {
                "strike": int(strike),
                "side": side_key,
                "ltp": round(ltp, 2),
                "oi": oi,
                "oi_chg": oi_chg,
                "oi_chg_pct": round((oi_chg / max(oi, 1)) * 100, 1),
                "volume": vol,
                "sell_pct": round(sell_pct * 100, 1),
                "net_change": round(net_chg, 2),
                "action": action,
                "micro_delta": micro_delta,
                "intensity": "MASSIVE" if abs(oi_chg) > MASSIVE_OI_CHG else "HEAVY" if abs(oi_chg) > HEAVY_OI_CHG else "MODERATE",
                "dist_from_atm": int(dist),
            }

            if side_key == "CE":
                ce_activity.append(entry)
                if action == "SELLER_WRITING" and abs(oi_chg) > SIGNIFICANT_OI_CHG:
                    ce_wall_strikes.append(entry)
                elif action == "SELLER_COVERING" and abs(oi_chg) > SIGNIFICANT_OI_CHG:
                    ce_cover_strikes.append(entry)
            else:
                pe_activity.append(entry)
                if action == "SELLER_WRITING" and abs(oi_chg) > SIGNIFICANT_OI_CHG:
                    pe_wall_strikes.append(entry)
                elif action == "SELLER_COVERING" and abs(oi_chg) > SIGNIFICANT_OI_CHG:
                    pe_cover_strikes.append(entry)

            # ── Flash Alert: sudden massive OI change ──
            if abs(oi_chg) > FLASH_ALERT_THRESHOLD:
                _flash_alerts.append({
                    "time": now.strftime("%H:%M:%S"),
                    "strike": int(strike),
                    "side": side_key,
                    "oi_chg": oi_chg,
                    "action": action,
                    "msg": f"{'MASSIVE' if abs(oi_chg) > MASSIVE_OI_CHG else 'HEAVY'} {action.replace('_', ' ')} at {int(strike)} {side_key} — OI {'+' if oi_chg > 0 else ''}{oi_chg:,}",
                    "type": "danger" if action == "SELLER_COVERING" else "warning",
                })

    # Sort by OI change magnitude
    ce_activity.sort(key=lambda x: abs(x["oi_chg"]), reverse=True)
    pe_activity.sort(key=lambda x: abs(x["oi_chg"]), reverse=True)
    ce_wall_strikes.sort(key=lambda x: x["oi_chg"], reverse=True)
    pe_wall_strikes.sort(key=lambda x: x["oi_chg"], reverse=True)
    ce_cover_strikes.sort(key=lambda x: abs(x["oi_chg"]), reverse=True)
    pe_cover_strikes.sort(key=lambda x: abs(x["oi_chg"]), reverse=True)

    # ══════════════════════════════════════════
    #  STEP 2: Cumulative seller position map
    # ══════════════════════════════════════════
    ce_seller_map = [{"strike": k, "cumulative_oi": v} for k, v in sorted(_cumulative_ce_seller.items()) if v > 0]
    pe_seller_map = [{"strike": k, "cumulative_oi": v} for k, v in sorted(_cumulative_pe_seller.items()) if v > 0]

    # Find biggest walls
    max_ce_wall = max(ce_wall_strikes, key=lambda x: x["oi_chg"], default=None)
    max_pe_wall = max(pe_wall_strikes, key=lambda x: x["oi_chg"], default=None)

    # ══════════════════════════════════════════
    #  STEP 3: Generate BUY signals from seller activity
    # ══════════════════════════════════════════
    signals = []
    net_ce_score = 0  # positive = sellers covering (bullish), negative = sellers writing (bearish)
    net_pe_score = 0

    # CE sellers covering = BULLISH → BUY CE
    if len(ce_cover_strikes) >= 2:
        cover_total = sum(abs(s["oi_chg"]) for s in ce_cover_strikes)
        net_ce_score += cover_total / 10000
        conviction = "HIGH" if cover_total > 200000 else "MODERATE"

        # Pick best CE strike for entry
        best_ce = None
        for s in sorted(chain.keys()):
            ce = chain[s].get("CE")
            if ce and ce.get("last_price", 0) >= 5 and s >= atm:
                best_ce = {"strike": int(s), "ltp": ce["last_price"]}
                break

        if best_ce:
            entry = best_ce["ltp"]
            signals.append({
                "signal": "BUY CE",
                "strike": f"{best_ce['strike']} CE",
                "entry": round(entry, 1),
                "target1": round(entry * 1.5, 1),
                "target2": round(entry * 2.0, 1),
                "stop_loss": round(entry * 0.6, 1),
                "reason": f"CE sellers covering at {len(ce_cover_strikes)} strikes (OI dropped {cover_total:,}). Sellers running = price going UP.",
                "conviction": conviction,
                "type": "bullish",
                "covering_strikes": [f"{s['strike']} CE: OI {s['oi_chg']:,}" for s in ce_cover_strikes[:3]],
            })

    # PE sellers covering = BEARISH → BUY PE
    if len(pe_cover_strikes) >= 2:
        cover_total = sum(abs(s["oi_chg"]) for s in pe_cover_strikes)
        net_pe_score += cover_total / 10000
        conviction = "HIGH" if cover_total > 200000 else "MODERATE"

        best_pe = None
        for s in sorted(chain.keys(), reverse=True):
            pe = chain[s].get("PE")
            if pe and pe.get("last_price", 0) >= 5 and s <= atm:
                best_pe = {"strike": int(s), "ltp": pe["last_price"]}
                break

        if best_pe:
            entry = best_pe["ltp"]
            signals.append({
                "signal": "BUY PE",
                "strike": f"{best_pe['strike']} PE",
                "entry": round(entry, 1),
                "target1": round(entry * 1.5, 1),
                "target2": round(entry * 2.0, 1),
                "stop_loss": round(entry * 0.6, 1),
                "reason": f"PE sellers covering at {len(pe_cover_strikes)} strikes (OI dropped {cover_total:,}). Put sellers running = downside coming.",
                "conviction": conviction,
                "type": "bearish",
                "covering_strikes": [f"{s['strike']} PE: OI {s['oi_chg']:,}" for s in pe_cover_strikes[:3]],
            })

    # Heavy PE writing = Support = BULLISH → BUY CE
    if len(pe_wall_strikes) >= 3 and total_pe_oi_added > 100000:
        net_ce_score += 3
        best_ce = None
        for s in sorted(chain.keys()):
            ce = chain[s].get("CE")
            if ce and ce.get("last_price", 0) >= 5 and s >= atm:
                best_ce = {"strike": int(s), "ltp": ce["last_price"]}
                break
        if best_ce:
            entry = best_ce["ltp"]
            signals.append({
                "signal": "BUY CE (Support)",
                "strike": f"{best_ce['strike']} CE",
                "entry": round(entry, 1),
                "target1": round(entry * 1.4, 1),
                "target2": round(entry * 1.8, 1),
                "stop_loss": round(entry * 0.6, 1),
                "reason": f"Heavy PUT writing at {len(pe_wall_strikes)} strikes (OI +{total_pe_oi_added:,}). Sellers confident market won't fall. Support zone = BUY CE.",
                "conviction": "MODERATE",
                "type": "bullish",
                "covering_strikes": [f"{s['strike']} PE: OI +{s['oi_chg']:,}" for s in pe_wall_strikes[:3]],
            })

    # Heavy CE writing = Resistance = AVOID CALLS
    if len(ce_wall_strikes) >= 3 and total_ce_oi_added > 100000:
        net_ce_score -= 5  # strong negative for CE buyers
        signals.append({
            "signal": "AVOID CE",
            "strike": "",
            "entry": 0, "target1": 0, "target2": 0, "stop_loss": 0,
            "reason": f"Heavy CALL writing at {len(ce_wall_strikes)} strikes (OI +{total_ce_oi_added:,}). Sellers capping upside. AVOID buying calls here.",
            "conviction": "HIGH",
            "type": "warning",
            "covering_strikes": [f"{s['strike']} CE: OI +{s['oi_chg']:,}" for s in ce_wall_strikes[:3]],
        })

    # ══════════════════════════════════════════
    #  STEP 4: Market stance conclusion
    # ══════════════════════════════════════════
    if net_ce_score > 3:
        stance = "BULLISH — Sellers exiting calls, BUY CE zone"
        stance_color = "green"
    elif net_pe_score > 3:
        stance = "BEARISH — Sellers exiting puts, BUY PE zone"
        stance_color = "red"
    elif total_ce_oi_added > total_pe_oi_added * 1.5:
        stance = "RANGE — Heavy call writing, upside capped"
        stance_color = "yellow"
    elif total_pe_oi_added > total_ce_oi_added * 1.5:
        stance = "SUPPORTED — Heavy put writing, downside limited"
        stance_color = "green"
    else:
        stance = "BALANCED — No clear seller bias"
        stance_color = "gray"

    # PCR
    total_ce_oi = sum((chain[s].get("CE") or {}).get("oi", 0) for s in strikes)
    total_pe_oi = sum((chain[s].get("PE") or {}).get("oi", 0) for s in strikes)
    pcr = round(total_pe_oi / max(total_ce_oi, 1), 3)

    return {
        "timestamp": now.isoformat(),
        "spot": round(spot, 2),
        "atm": atm,

        # Market stance
        "stance": stance,
        "stance_color": stance_color,
        "pcr": pcr,

        # Cumulative seller summary
        "ce_oi_added": total_ce_oi_added,
        "ce_oi_removed": total_ce_oi_removed,
        "pe_oi_added": total_pe_oi_added,
        "pe_oi_removed": total_pe_oi_removed,

        # Seller walls (where they're building)
        "ce_walls": ce_wall_strikes[:5],
        "pe_walls": pe_wall_strikes[:5],
        "max_ce_wall": {"strike": max_ce_wall["strike"], "oi_chg": max_ce_wall["oi_chg"]} if max_ce_wall else None,
        "max_pe_wall": {"strike": max_pe_wall["strike"], "oi_chg": max_pe_wall["oi_chg"]} if max_pe_wall else None,

        # Seller exits (where they're covering)
        "ce_covering": ce_cover_strikes[:5],
        "pe_covering": pe_cover_strikes[:5],

        # Cumulative seller map (for heatmap)
        "ce_seller_map": ce_seller_map[-10:],
        "pe_seller_map": pe_seller_map[-10:],

        # BUY signals
        "signals": signals,

        # Flash alerts
        "flash_alerts": list(_flash_alerts)[-5:],

        # All activity (top 15 by OI change)
        "ce_activity": ce_activity[:10],
        "pe_activity": pe_activity[:10],

        # Counts
        "ce_writing_count": len(ce_wall_strikes),
        "pe_writing_count": len(pe_wall_strikes),
        "ce_covering_count": len(ce_cover_strikes),
        "pe_covering_count": len(pe_cover_strikes),
    }


def _empty() -> dict:
    return {
        "timestamp": datetime.now(IST).isoformat(),
        "stance": "NO DATA", "stance_color": "gray", "spot": 0, "atm": 0, "pcr": 0,
        "ce_oi_added": 0, "ce_oi_removed": 0, "pe_oi_added": 0, "pe_oi_removed": 0,
        "ce_walls": [], "pe_walls": [], "max_ce_wall": None, "max_pe_wall": None,
        "ce_covering": [], "pe_covering": [],
        "ce_seller_map": [], "pe_seller_map": [],
        "signals": [], "flash_alerts": [],
        "ce_activity": [], "pe_activity": [],
        "ce_writing_count": 0, "pe_writing_count": 0,
        "ce_covering_count": 0, "pe_covering_count": 0,
    }
