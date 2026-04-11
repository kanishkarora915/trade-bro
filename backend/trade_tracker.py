"""Trade Tracker — Paper trading with auto exit tracking + P&L + reports.

Tracks every signal from Command Center:
- Entry recorded when signal fires
- Exit auto-tracked: SL hit, T1 hit, T2 hit, time stop, manual
- Real P&L calculated per trade
- Daily/weekly/monthly reports generated
- Win rate, avg return, drawdown tracked

Persists to disk — survives restarts.
"""

import json
import os
import time
from datetime import datetime, timezone, timedelta
from collections import defaultdict

IST = timezone(timedelta(hours=5, minutes=30))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
TRACKER_DIR = os.path.join(DATA_DIR, "trade_tracker")


def _ensure_dir():
    os.makedirs(TRACKER_DIR, exist_ok=True)


def _today() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d")


def _load_trades(date: str) -> list[dict]:
    _ensure_dir()
    path = os.path.join(TRACKER_DIR, f"{date}.json")
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_trades(date: str, trades: list[dict]):
    _ensure_dir()
    path = os.path.join(TRACKER_DIR, f"{date}.json")
    with open(path, "w") as f:
        json.dump(trades, f, default=str, indent=2)


# ── Active trade state ──
_active: dict | None = None
_entry_time: float = 0


def open_trade(signal: str, trade: dict, reason: str, conviction: float) -> dict:
    """Record a new trade entry."""
    global _active, _entry_time
    now = datetime.now(IST)

    _active = {
        "id": f"T{int(time.time())}",
        "date": _today(),
        "signal": signal,
        "strike": trade.get("strike", ""),
        "side": trade.get("side", ""),
        "entry": trade.get("entry", 0),
        "stop_loss": trade.get("stop_loss", 0),
        "target1": trade.get("target1", 0),
        "target2": trade.get("target2", 0),
        "lots": trade.get("lots", 0),
        "lot_size": trade.get("lot_size", 0),
        "capital_used": trade.get("capital_used", 0),
        "reason": reason[:200],
        "conviction": conviction,
        "entry_time": now.isoformat(),
        "status": "OPEN",
        "exit_price": 0,
        "exit_time": "",
        "exit_reason": "",
        "pnl_pct": 0,
        "pnl_abs": 0,
        "hold_time_min": 0,
    }
    _entry_time = time.time()
    return _active


def check_and_close(current_ltp: float, oi_alert: str = "") -> dict | None:
    """Check if active trade should be closed. Returns closed trade or None."""
    global _active, _entry_time
    if not _active or _active["status"] != "OPEN":
        return None

    entry = _active["entry"]
    if entry <= 0 or current_ltp <= 0:
        return None

    now = datetime.now(IST)
    hold_min = (time.time() - _entry_time) / 60
    pnl_pct = (current_ltp - entry) / entry * 100

    exit_reason = ""

    # SL Hit
    if current_ltp <= _active["stop_loss"]:
        exit_reason = "SL HIT"

    # T1 Hit (partial — we track as full for paper trading)
    elif current_ltp >= _active["target1"] and current_ltp < _active["target2"]:
        exit_reason = "T1 HIT"

    # T2 Hit
    elif current_ltp >= _active["target2"]:
        exit_reason = "T2 HIT"

    # Time stop: 30 min no significant movement
    elif hold_min >= 30 and abs(pnl_pct) < 5:
        exit_reason = "TIME STOP (30 min, <5% move)"

    # OI-based exit
    elif oi_alert and "EXIT" in oi_alert.upper():
        exit_reason = f"OI EXIT: {oi_alert[:50]}"

    if not exit_reason:
        return None  # trade still open

    # Close trade
    lot_total = _active["lots"] * _active["lot_size"]
    _active["exit_price"] = round(current_ltp, 1)
    _active["exit_time"] = now.isoformat()
    _active["exit_reason"] = exit_reason
    _active["pnl_pct"] = round(pnl_pct, 2)
    _active["pnl_abs"] = round((current_ltp - entry) * lot_total, 0)
    _active["hold_time_min"] = round(hold_min, 1)
    _active["status"] = "CLOSED"

    # Save to disk
    trades = _load_trades(_active["date"])
    trades.append(_active)
    _save_trades(_active["date"], trades)

    closed = _active.copy()
    _active = None
    _entry_time = 0
    return closed


def get_active() -> dict | None:
    """Get currently active trade."""
    return _active


def get_today_trades() -> list[dict]:
    return _load_trades(_today())


def get_daily_report(date: str = "") -> dict:
    """Generate daily P&L report."""
    if not date:
        date = _today()
    trades = _load_trades(date)
    if not trades:
        return {"date": date, "total_trades": 0, "wins": 0, "losses": 0,
                "win_rate": 0, "total_pnl": 0, "avg_pnl_pct": 0, "trades": [],
                "best_trade": None, "worst_trade": None, "max_drawdown": 0}

    closed = [t for t in trades if t.get("status") == "CLOSED"]
    wins = [t for t in closed if t.get("pnl_pct", 0) > 0]
    losses = [t for t in closed if t.get("pnl_pct", 0) <= 0]
    total_pnl = sum(t.get("pnl_abs", 0) for t in closed)
    avg_pnl = sum(t.get("pnl_pct", 0) for t in closed) / len(closed) if closed else 0
    win_rate = (len(wins) / len(closed) * 100) if closed else 0

    best = max(closed, key=lambda t: t.get("pnl_pct", 0), default=None)
    worst = min(closed, key=lambda t: t.get("pnl_pct", 0), default=None)

    # Max drawdown
    running_pnl = 0
    peak = 0
    max_dd = 0
    for t in closed:
        running_pnl += t.get("pnl_abs", 0)
        if running_pnl > peak:
            peak = running_pnl
        dd = peak - running_pnl
        if dd > max_dd:
            max_dd = dd

    return {
        "date": date,
        "total_trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 1),
        "total_pnl": round(total_pnl, 0),
        "avg_pnl_pct": round(avg_pnl, 2),
        "best_trade": {"strike": best["strike"], "pnl": best["pnl_pct"]} if best else None,
        "worst_trade": {"strike": worst["strike"], "pnl": worst["pnl_pct"]} if worst else None,
        "max_drawdown": round(max_dd, 0),
        "trades": closed[-10:],  # last 10
    }


def get_weekly_report() -> dict:
    """Generate weekly report (last 5 trading days)."""
    today = datetime.now(IST)
    daily_reports = []
    total_pnl = 0
    total_trades = 0
    total_wins = 0

    for i in range(7):
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        report = get_daily_report(date)
        if report["total_trades"] > 0:
            daily_reports.append(report)
            total_pnl += report["total_pnl"]
            total_trades += report["total_trades"]
            total_wins += report["wins"]
        if len(daily_reports) >= 5:
            break

    return {
        "period": "Last 5 trading days",
        "total_pnl": round(total_pnl, 0),
        "total_trades": total_trades,
        "win_rate": round(total_wins / max(total_trades, 1) * 100, 1),
        "avg_daily_pnl": round(total_pnl / max(len(daily_reports), 1), 0),
        "daily_reports": daily_reports,
    }


def get_monthly_report() -> dict:
    """Generate monthly report."""
    today = datetime.now(IST)
    month = today.strftime("%Y-%m")
    total_pnl = 0
    total_trades = 0
    total_wins = 0
    daily_pnls = []

    for i in range(31):
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        if not date.startswith(month):
            continue
        report = get_daily_report(date)
        if report["total_trades"] > 0:
            total_pnl += report["total_pnl"]
            total_trades += report["total_trades"]
            total_wins += report["wins"]
            daily_pnls.append({"date": date, "pnl": report["total_pnl"], "trades": report["total_trades"]})

    return {
        "month": month,
        "total_pnl": round(total_pnl, 0),
        "total_trades": total_trades,
        "win_rate": round(total_wins / max(total_trades, 1) * 100, 1),
        "trading_days": len(daily_pnls),
        "avg_daily_pnl": round(total_pnl / max(len(daily_pnls), 1), 0),
        "daily_pnls": daily_pnls,
    }
