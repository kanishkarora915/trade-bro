"""Auto-Tune Engine — Weekly pattern analysis to improve signal quality.

Runs every Friday night (or on-demand). Analyzes all paper trades from the week:
1. Which detector combinations led to WINNING trades?
2. Which regimes were profitable vs losing?
3. What IVR/GEX ranges worked best?
4. Were pullback or breakout entries better?
5. What SL type (OI wall vs fixed) performed better?
6. What time of day had best win rate?

Output: Tuning recommendations + auto-adjust weights for next week.
Persists to disk.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from collections import defaultdict

IST = timezone(timedelta(hours=5, minutes=30))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
TUNE_DIR = os.path.join(DATA_DIR, "auto_tune")


def _ensure_dir():
    os.makedirs(TUNE_DIR, exist_ok=True)


def _load_trades(days: int = 7) -> list[dict]:
    """Load all paper trades from last N days."""
    trades = []
    today = datetime.now(IST)
    pt_dir = os.path.join(DATA_DIR, "paper_trader")
    sniper_dir = os.path.join(DATA_DIR, "sniper")
    cmd_dir = os.path.join(DATA_DIR, "command_center")

    for i in range(days):
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        for d in [pt_dir, sniper_dir, cmd_dir]:
            for prefix in ["trades_", "history_"]:
                path = os.path.join(d, f"{prefix}{date}.json")
                if os.path.exists(path):
                    try:
                        with open(path) as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                trades.extend(data)
                    except Exception:
                        pass
    return trades


def analyze_patterns(days: int = 7) -> dict:
    """Analyze all trades and find winning/losing patterns."""
    trades = _load_trades(days)

    if not trades:
        return {
            "status": "NO DATA",
            "trades_analyzed": 0,
            "message": "No trades found. Paper trade for a week first.",
            "recommendations": [],
            "adjustments": {},
        }

    # Separate wins and losses
    closed = [t for t in trades if t.get("status") == "CLOSED" or t.get("exit_reason")]
    wins = [t for t in closed if (t.get("final_pnl_pct") or t.get("exit_pnl") or t.get("pnl_pct", 0)) > 0]
    losses = [t for t in closed if (t.get("final_pnl_pct") or t.get("exit_pnl") or t.get("pnl_pct", 0)) <= 0]

    total = len(closed)
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = round(win_count / max(total, 1) * 100, 1)

    # ── Pattern 1: Exit reason analysis ──
    exit_reasons = defaultdict(lambda: {"wins": 0, "losses": 0, "total_pnl": 0})
    for t in closed:
        reason = t.get("exit_reason", t.get("exit_reason", "UNKNOWN"))
        pnl = t.get("final_pnl_pct") or t.get("exit_pnl") or t.get("pnl_pct", 0)
        if pnl > 0:
            exit_reasons[reason]["wins"] += 1
        else:
            exit_reasons[reason]["losses"] += 1
        exit_reasons[reason]["total_pnl"] += pnl

    # ── Pattern 2: Source analysis (SNIPER vs COMMAND) ──
    source_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "total_pnl": 0})
    for t in closed:
        source = t.get("source", "UNKNOWN")
        pnl = t.get("final_pnl_pct") or t.get("exit_pnl") or t.get("pnl_pct", 0)
        if pnl > 0:
            source_stats[source]["wins"] += 1
        else:
            source_stats[source]["losses"] += 1
        source_stats[source]["total_pnl"] += pnl

    # ── Pattern 3: Side analysis (CE vs PE) ──
    side_stats = defaultdict(lambda: {"wins": 0, "losses": 0})
    for t in closed:
        side = t.get("side", "UNKNOWN")
        pnl = t.get("final_pnl_pct") or t.get("exit_pnl") or t.get("pnl_pct", 0)
        if pnl > 0:
            side_stats[side]["wins"] += 1
        else:
            side_stats[side]["losses"] += 1

    # ── Pattern 4: Hold time analysis ──
    win_hold_times = [t.get("hold_time_min", 0) for t in wins if t.get("hold_time_min")]
    loss_hold_times = [t.get("hold_time_min", 0) for t in losses if t.get("hold_time_min")]
    avg_win_hold = round(sum(win_hold_times) / max(len(win_hold_times), 1), 1)
    avg_loss_hold = round(sum(loss_hold_times) / max(len(loss_hold_times), 1), 1)

    # ── Pattern 5: Time of day analysis ──
    hour_stats = defaultdict(lambda: {"wins": 0, "losses": 0})
    for t in closed:
        entry_time = t.get("entry_time", "")
        if "T" in str(entry_time):
            try:
                hour = int(str(entry_time).split("T")[1][:2])
                pnl = t.get("final_pnl_pct") or t.get("exit_pnl") or t.get("pnl_pct", 0)
                if pnl > 0:
                    hour_stats[hour]["wins"] += 1
                else:
                    hour_stats[hour]["losses"] += 1
            except Exception:
                pass

    # ── Pattern 6: Consecutive win/loss streaks ──
    max_win_streak = 0
    max_loss_streak = 0
    current_streak = 0
    for t in closed:
        pnl = t.get("final_pnl_pct") or t.get("exit_pnl") or t.get("pnl_pct", 0)
        if pnl > 0:
            if current_streak > 0:
                current_streak += 1
            else:
                current_streak = 1
            max_win_streak = max(max_win_streak, current_streak)
        else:
            if current_streak < 0:
                current_streak -= 1
            else:
                current_streak = -1
            max_loss_streak = max(max_loss_streak, abs(current_streak))

    # ══════════════════════════════════════════
    #  RECOMMENDATIONS
    # ══════════════════════════════════════════
    recommendations = []
    adjustments = {}

    # Win rate check
    if win_rate < 40:
        recommendations.append({
            "priority": "CRITICAL",
            "finding": f"Win rate {win_rate}% — below breakeven",
            "action": "Increase signal threshold. Only take trades with NET votes ≥7 (currently ≥5).",
            "adjustment": "command_center.BUY_NET_THRESHOLD: 5 → 7",
        })
        adjustments["buy_net_threshold"] = 7
    elif win_rate < 50:
        recommendations.append({
            "priority": "HIGH",
            "finding": f"Win rate {win_rate}% — marginal",
            "action": "Tighten entry criteria. Require 6+ NET votes for BUY.",
            "adjustment": "command_center.BUY_NET_THRESHOLD: 5 → 6",
        })
        adjustments["buy_net_threshold"] = 6
    elif win_rate >= 60:
        recommendations.append({
            "priority": "INFO",
            "finding": f"Win rate {win_rate}% — GOOD",
            "action": "System working well. Consider slightly loosening for more trades.",
        })

    # SL analysis
    sl_hits = sum(1 for t in closed if "SL" in str(t.get("exit_reason", "")))
    sl_rate = sl_hits / max(total, 1) * 100
    if sl_rate > 50:
        recommendations.append({
            "priority": "HIGH",
            "finding": f"SL hit rate {sl_rate:.0f}% — too many stops",
            "action": "SL too tight. Widen SL by 5% or use wider OI walls.",
            "adjustment": "command_center.MAX_SL_PCT: 15% → 20%",
        })
        adjustments["max_sl_pct"] = 0.20
    elif sl_rate < 20:
        recommendations.append({
            "priority": "INFO",
            "finding": f"SL hit rate {sl_rate:.0f}% — very few stops",
            "action": "SL might be too wide. Tighten to 12% for better risk/reward.",
        })

    # Time stop analysis
    time_stops = sum(1 for t in closed if "TIME" in str(t.get("exit_reason", "")))
    if time_stops > total * 0.3:
        recommendations.append({
            "priority": "MODERATE",
            "finding": f"{time_stops}/{total} trades exited on time stop",
            "action": "Too many flat trades. Improve entry timing — wait for momentum confirmation.",
        })

    # Hold time
    if avg_win_hold > 0 and avg_loss_hold > 0:
        if avg_loss_hold > avg_win_hold:
            recommendations.append({
                "priority": "HIGH",
                "finding": f"Losses held {avg_loss_hold}min vs wins {avg_win_hold}min",
                "action": "Cutting winners too early, holding losers too long. Tighten time stop to 20 min.",
                "adjustment": "sniper.TIME_STOP: 30min → 20min",
            })
            adjustments["time_stop_min"] = 20

    # CE vs PE
    for side, stats in side_stats.items():
        total_side = stats["wins"] + stats["losses"]
        if total_side >= 3:
            wr = stats["wins"] / total_side * 100
            if wr < 35:
                recommendations.append({
                    "priority": "MODERATE",
                    "finding": f"{side} win rate only {wr:.0f}% ({stats['wins']}/{total_side})",
                    "action": f"Consider reducing {side} trades or tightening {side} criteria.",
                })

    # Best/worst hours
    best_hour = max(hour_stats.items(), key=lambda x: x[1]["wins"] - x[1]["losses"], default=None)
    worst_hour = min(hour_stats.items(), key=lambda x: x[1]["wins"] - x[1]["losses"], default=None)
    if best_hour:
        recommendations.append({
            "priority": "INFO",
            "finding": f"Best hour: {best_hour[0]}:00 ({best_hour[1]['wins']}W/{best_hour[1]['losses']}L)",
            "action": "Consider focusing trades around this time.",
        })
    if worst_hour and (worst_hour[1]["losses"] > worst_hour[1]["wins"]):
        recommendations.append({
            "priority": "MODERATE",
            "finding": f"Worst hour: {worst_hour[0]}:00 ({worst_hour[1]['wins']}W/{worst_hour[1]['losses']}L)",
            "action": "Avoid or reduce trades at this hour.",
        })

    # ══════════════════════════════════════════
    #  SAVE REPORT
    # ══════════════════════════════════════════
    report = {
        "timestamp": datetime.now(IST).isoformat(),
        "period_days": days,
        "trades_analyzed": total,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": win_rate,
        "exit_reasons": {k: dict(v) for k, v in exit_reasons.items()},
        "source_stats": {k: dict(v) for k, v in source_stats.items()},
        "side_stats": {k: dict(v) for k, v in side_stats.items()},
        "hour_stats": {str(k): dict(v) for k, v in sorted(hour_stats.items())},
        "avg_win_hold_min": avg_win_hold,
        "avg_loss_hold_min": avg_loss_hold,
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
        "sl_hit_rate": round(sl_rate, 1),
        "recommendations": recommendations,
        "adjustments": adjustments,
        "status": "ANALYZED",
    }

    # Save to disk
    try:
        _ensure_dir()
        date = datetime.now(IST).strftime("%Y-%m-%d")
        with open(os.path.join(TUNE_DIR, f"tune_{date}.json"), "w") as f:
            json.dump(report, f, default=str, indent=2)
    except Exception:
        pass

    return report


def get_latest_report() -> dict:
    """Get most recent auto-tune report."""
    _ensure_dir()
    files = sorted([f for f in os.listdir(TUNE_DIR) if f.startswith("tune_")], reverse=True)
    if files:
        try:
            with open(os.path.join(TUNE_DIR, files[0])) as f:
                return json.load(f)
        except Exception:
            pass
    return {"status": "NO DATA", "trades_analyzed": 0, "recommendations": []}
