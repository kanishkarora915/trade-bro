"""Seller Footprint Engine — Track option writers' activity for buyer edge.

Core principle: As a BUYER, we track SELLERS because:
- Seller covering (OI drop + price up)    = BIG MOVE coming → BUY opportunity
- Seller writing heavily (OI up + price down) = Range-bound → AVOID
- Sudden seller exit                      = Explosive move imminent → BUY NOW
- Slow OI injection by seller             = Building position → Watch for reversal

OI + Price Matrix:
┌──────────────┬─────────────┬──────────────┐
│              │ Price UP    │ Price DOWN   │
├──────────────┼─────────────┼──────────────┤
│ OI UP        │ Long Build  │ SHORT BUILD  │ ← Sellers entering
│ OI DOWN      │ SHORT COVER │ Long Unwind  │ ← Sellers exiting
└──────────────┴─────────────┴──────────────┘
"""

from datetime import datetime, timezone, timedelta
from collections import deque

IST = timezone(timedelta(hours=5, minutes=30))


def _classify_oi_price(oi_chg: float, price_chg: float) -> tuple[str, str, str]:
    """Classify OI + Price combination. Returns (action, emoji, color)."""
    if oi_chg > 0 and price_chg < 0:
        return "SHORT BUILD", "🔴", "red"       # Sellers writing — bearish
    if oi_chg < 0 and price_chg > 0:
        return "SHORT COVER", "🟢", "green"     # Sellers exiting — bullish!
    if oi_chg > 0 and price_chg > 0:
        return "LONG BUILD", "🔵", "blue"       # Buyers entering — bullish
    if oi_chg < 0 and price_chg < 0:
        return "LONG UNWIND", "🟡", "yellow"    # Buyers exiting — bearish
    return "NEUTRAL", "⚪", "gray"


def analyze(chain: dict, spot: float, atm: int, strike_step: int = 50,
            prev_snapshot: dict | None = None) -> dict:
    """Analyze seller footprints across the option chain.

    Args:
        chain: {strike: {CE: {...}, PE: {...}}} with oi, oi_day_change, last_price, volume, buy_pct
        spot: current spot price
        atm: ATM strike
        strike_step: 50 for NIFTY, 100 for BANKNIFTY
        prev_snapshot: previous cycle's OI snapshot for velocity detection

    Returns: Complete seller footprint analysis dict
    """
    now = datetime.now(IST)
    h, m = now.hour, now.minute
    market_active = (h == 9 and m >= 15) or (10 <= h <= 14) or (h == 15 and m <= 30)

    if not chain or spot <= 0:
        return _empty_result(now)

    strikes = sorted(chain.keys())
    if not strikes:
        return _empty_result(now)

    # ── Per-strike analysis ──
    strike_analysis = []
    total_ce_oi_chg = 0
    total_pe_oi_chg = 0
    total_ce_oi = 0
    total_pe_oi = 0

    # Seller activity aggregation
    ce_short_build = []     # strikes where CE sellers are writing
    pe_short_build = []     # strikes where PE sellers are writing
    ce_short_cover = []     # strikes where CE sellers are covering
    pe_short_cover = []     # strikes where PE sellers are covering
    sudden_entries = []     # sudden large seller entries
    slow_injections = []    # gradual OI buildup

    for strike in strikes:
        sides = chain[strike]
        dist = abs(strike - atm) / strike_step
        if dist > 10:
            continue  # only ±10 strikes from ATM

        for side_key in ("CE", "PE"):
            info = sides.get(side_key)
            if not info:
                continue

            oi = info.get("oi", 0)
            oi_chg = info.get("oi_day_change", 0)
            ltp = info.get("last_price", 0)
            vol = info.get("volume", 0)
            buy_pct = info.get("buy_pct", 0.5)
            sell_pct = 1 - buy_pct
            net_change = info.get("net_change", 0)

            if side_key == "CE":
                total_ce_oi += oi
                total_ce_oi_chg += oi_chg
            else:
                total_pe_oi += oi
                total_pe_oi_chg += oi_chg

            action, emoji, color = _classify_oi_price(oi_chg, net_change)

            # Skip low activity strikes
            if abs(oi_chg) < 1000 and vol < 500:
                continue

            entry = {
                "strike": int(strike),
                "side": side_key,
                "ltp": round(ltp, 2),
                "oi": oi,
                "oi_chg": oi_chg,
                "oi_chg_pct": round((oi_chg / oi * 100) if oi > 0 else 0, 1),
                "volume": vol,
                "buy_pct": round(buy_pct * 100, 1),
                "sell_pct": round(sell_pct * 100, 1),
                "net_change": round(net_change, 2),
                "action": action,
                "emoji": emoji,
                "color": color,
                "dist_from_atm": int(dist),
                "is_atm": dist < 1,
            }
            strike_analysis.append(entry)

            # ── Categorize seller activity ──

            # SHORT BUILD: OI increasing + price dropping + high sell %
            if action == "SHORT BUILD" and abs(oi_chg) > 5000:
                target = ce_short_build if side_key == "CE" else pe_short_build
                target.append({
                    **entry,
                    "intensity": "HEAVY" if abs(oi_chg) > 50000 else "MODERATE" if abs(oi_chg) > 20000 else "LIGHT",
                    "detail": f"{'Heavy' if abs(oi_chg) > 50000 else 'Moderate'} {side_key} writing at {int(strike)} — OI +{oi_chg:,}, sellers {'aggressive' if sell_pct > 60 else 'active'}",
                })

            # SHORT COVER: OI decreasing + price rising
            elif action == "SHORT COVER" and abs(oi_chg) > 5000:
                target = ce_short_cover if side_key == "CE" else pe_short_cover
                target.append({
                    **entry,
                    "intensity": "HEAVY" if abs(oi_chg) > 50000 else "MODERATE" if abs(oi_chg) > 20000 else "LIGHT",
                    "detail": f"{'Heavy' if abs(oi_chg) > 50000 else 'Moderate'} {side_key} covering at {int(strike)} — OI {oi_chg:,}, sellers EXITING",
                    "buyer_signal": True,  # This is bullish for buyers!
                })

            # SUDDEN ENTRY: Very large OI spike at single strike
            if oi_chg > 100000 and sell_pct > 55:
                sudden_entries.append({
                    **entry,
                    "detail": f"SUDDEN {side_key} seller entry at {int(strike)} — OI +{oi_chg:,} ({sell_pct:.0f}% sell side)",
                    "threat_level": "HIGH" if oi_chg > 200000 else "MEDIUM",
                })

            # SLOW INJECTION: Moderate OI buildup with high sell %
            if 10000 < oi_chg < 100000 and sell_pct > 60 and vol > 5000:
                slow_injections.append({
                    **entry,
                    "detail": f"Slow {side_key} OI injection at {int(strike)} — OI +{oi_chg:,}, {sell_pct:.0f}% sell side, vol {vol:,}",
                })

    # ── OI Velocity (compare with previous snapshot) ──
    oi_velocity = []
    if prev_snapshot:
        for strike in strikes:
            for side_key in ("CE", "PE"):
                info = chain.get(strike, {}).get(side_key)
                prev_info = prev_snapshot.get(str(int(strike)), {}).get(side_key, {})
                if info and prev_info:
                    curr_oi = info.get("oi", 0)
                    prev_oi = prev_info.get("oi", 0)
                    delta = curr_oi - prev_oi
                    if abs(delta) > 10000:
                        oi_velocity.append({
                            "strike": int(strike),
                            "side": side_key,
                            "delta": delta,
                            "direction": "ADDING" if delta > 0 else "EXITING",
                            "speed": "FAST" if abs(delta) > 50000 else "MODERATE",
                        })

    # ── Seller Walls (resistance/support from OI) ──
    ce_wall = max(strike_analysis, key=lambda x: x["oi"] if x["side"] == "CE" else 0, default=None)
    pe_wall = max(strike_analysis, key=lambda x: x["oi"] if x["side"] == "PE" else 0, default=None)

    # ── Net Seller Position ──
    net_ce_selling = sum(1 for s in ce_short_build if s["intensity"] in ("HEAVY", "MODERATE"))
    net_pe_selling = sum(1 for s in pe_short_build if s["intensity"] in ("HEAVY", "MODERATE"))
    net_ce_covering = sum(1 for s in ce_short_cover if s["intensity"] in ("HEAVY", "MODERATE"))
    net_pe_covering = sum(1 for s in pe_short_cover if s["intensity"] in ("HEAVY", "MODERATE"))

    # ── Buyer Signals from Seller Activity ──
    buyer_signals = []

    # Heavy CE short covering = BULLISH → BUY CE
    if net_ce_covering >= 2:
        buyer_signals.append({
            "signal": "BUY CE",
            "reason": f"Heavy CE short covering at {net_ce_covering} strikes — sellers running, expect up move",
            "conviction": "HIGH" if net_ce_covering >= 3 else "MODERATE",
            "type": "bullish",
        })

    # Heavy PE short covering = BEARISH (but less useful for buyer)
    if net_pe_covering >= 2:
        buyer_signals.append({
            "signal": "BUY PE",
            "reason": f"Heavy PE short covering at {net_pe_covering} strikes — put sellers exiting, down move possible",
            "conviction": "HIGH" if net_pe_covering >= 3 else "MODERATE",
            "type": "bearish",
        })

    # Heavy PE writing = Support building = BULLISH
    if net_pe_selling >= 3:
        buyer_signals.append({
            "signal": "SUPPORT BUILDING",
            "reason": f"Heavy PE writing at {net_pe_selling} strikes — sellers confident market won't fall, support zone",
            "conviction": "HIGH" if net_pe_selling >= 4 else "MODERATE",
            "type": "bullish",
        })

    # Heavy CE writing = Resistance building = BEARISH
    if net_ce_selling >= 3:
        buyer_signals.append({
            "signal": "RESISTANCE BUILDING",
            "reason": f"Heavy CE writing at {net_ce_selling} strikes — sellers capping upside, resistance zone",
            "conviction": "HIGH" if net_ce_selling >= 4 else "MODERATE",
            "type": "bearish",
        })

    # Sudden seller exit = EXPLOSIVE MOVE
    if sudden_entries:
        for se in sudden_entries:
            buyer_signals.append({
                "signal": f"SUDDEN SELLER ENTRY",
                "reason": se["detail"],
                "conviction": se["threat_level"],
                "type": "warning",
            })

    # ── Overall Market Stance ──
    if net_ce_covering > net_ce_selling and net_ce_covering >= 2:
        market_stance = "SELLERS EXITING CALLS — Bullish"
        stance_color = "green"
    elif net_pe_covering > net_pe_selling and net_pe_covering >= 2:
        market_stance = "SELLERS EXITING PUTS — Bearish"
        stance_color = "red"
    elif net_pe_selling > net_ce_selling + 1:
        market_stance = "HEAVY PUT WRITING — Support Building"
        stance_color = "green"
    elif net_ce_selling > net_pe_selling + 1:
        market_stance = "HEAVY CALL WRITING — Resistance Building"
        stance_color = "red"
    else:
        market_stance = "BALANCED — No clear seller bias"
        stance_color = "gray"

    # PCR from OI
    pcr = round(total_pe_oi / max(total_ce_oi, 1), 3)
    pcr_signal = "OVERSOLD" if pcr < 0.7 else "OVERBOUGHT" if pcr > 1.3 else "NEUTRAL"

    return {
        "timestamp": now.isoformat(),
        "market_active": market_active,
        "spot": round(spot, 2),
        "atm": atm,

        # Overall stance
        "market_stance": market_stance,
        "stance_color": stance_color,
        "pcr": pcr,
        "pcr_signal": pcr_signal,

        # OI summary
        "total_ce_oi": total_ce_oi,
        "total_pe_oi": total_pe_oi,
        "total_ce_oi_chg": total_ce_oi_chg,
        "total_pe_oi_chg": total_pe_oi_chg,

        # Seller activity breakdown
        "ce_short_build": sorted(ce_short_build, key=lambda x: abs(x["oi_chg"]), reverse=True)[:5],
        "pe_short_build": sorted(pe_short_build, key=lambda x: abs(x["oi_chg"]), reverse=True)[:5],
        "ce_short_cover": sorted(ce_short_cover, key=lambda x: abs(x["oi_chg"]), reverse=True)[:5],
        "pe_short_cover": sorted(pe_short_cover, key=lambda x: abs(x["oi_chg"]), reverse=True)[:5],

        # Special events
        "sudden_entries": sudden_entries[:3],
        "slow_injections": sorted(slow_injections, key=lambda x: x["oi_chg"], reverse=True)[:5],
        "oi_velocity": oi_velocity[:10],

        # Walls
        "ce_wall": {"strike": int(ce_wall["strike"]), "oi": ce_wall["oi"]} if ce_wall and ce_wall["side"] == "CE" else None,
        "pe_wall": {"strike": int(pe_wall["strike"]), "oi": pe_wall["oi"]} if pe_wall and pe_wall["side"] == "PE" else None,

        # Buyer signals derived from seller activity
        "buyer_signals": buyer_signals,

        # Counts
        "ce_selling_strikes": net_ce_selling,
        "pe_selling_strikes": net_pe_selling,
        "ce_covering_strikes": net_ce_covering,
        "pe_covering_strikes": net_pe_covering,

        # Full strike data (sorted by OI change)
        "strike_data": sorted(strike_analysis, key=lambda x: abs(x["oi_chg"]), reverse=True)[:20],
    }


def _empty_result(now) -> dict:
    return {
        "timestamp": now.isoformat(), "market_active": False,
        "market_stance": "NO DATA", "stance_color": "gray",
        "spot": 0, "atm": 0, "pcr": 0, "pcr_signal": "NEUTRAL",
        "total_ce_oi": 0, "total_pe_oi": 0,
        "total_ce_oi_chg": 0, "total_pe_oi_chg": 0,
        "ce_short_build": [], "pe_short_build": [],
        "ce_short_cover": [], "pe_short_cover": [],
        "sudden_entries": [], "slow_injections": [], "oi_velocity": [],
        "ce_wall": None, "pe_wall": None,
        "buyer_signals": [], "strike_data": [],
        "ce_selling_strikes": 0, "pe_selling_strikes": 0,
        "ce_covering_strikes": 0, "pe_covering_strikes": 0,
    }
