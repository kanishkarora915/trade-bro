"""Paper Trader — Full paper trading system with live LTP tracking.

Auto-fetches signals from Sniper/Command Center.
Tracks tick-to-tick LTP of active positions.
Daily/weekly/monthly reports with capital tracking.

Settings editable: capital, lot sizes per index.
All data persisted to disk.
"""

import json
import os
import time
from datetime import datetime, timezone, timedelta
from collections import deque

IST = timezone(timedelta(hours=5, minutes=30))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
PT_DIR = os.path.join(DATA_DIR, "paper_trader")

# ── Default Settings ──
_settings = {
    "capital": 1000000,
    "lot_sizes": {"NIFTY": 65, "BANKNIFTY": 30, "SENSEX": 20},
    "max_sl_pct": 15,
    "max_positions": 3,
    "starting_capital": 1000000,  # never changes — for P&L % calc
}

# ── State ──
_positions: list[dict] = []       # active positions
_closed_today: list[dict] = []    # closed trades today
_capital_used: float = 0
_pnl_history: deque = deque(maxlen=500)  # (timestamp, equity)
_last_auto_fetch_ts: float = 0
AUTO_FETCH_COOLDOWN = 300  # 5 min between auto-fetches


def _ensure_dir():
    os.makedirs(PT_DIR, exist_ok=True)


def _save_settings():
    _ensure_dir()
    with open(os.path.join(PT_DIR, "settings.json"), "w") as f:
        json.dump(_settings, f)


def _load_settings():
    global _settings
    path = os.path.join(PT_DIR, "settings.json")
    if os.path.exists(path):
        try:
            with open(path) as f:
                loaded = json.load(f)
                _settings.update(loaded)
        except Exception:
            pass


def _save_day_trades(date: str, trades: list):
    _ensure_dir()
    path = os.path.join(PT_DIR, f"trades_{date}.json")
    with open(path, "w") as f:
        json.dump(trades, f, default=str, indent=2)


def _load_day_trades(date: str) -> list:
    path = os.path.join(PT_DIR, f"trades_{date}.json")
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _today() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d")


# ── Init ──
_load_settings()
_closed_today = _load_day_trades(_today())


def update_settings(capital: int = None, lot_sizes: dict = None, max_sl_pct: float = None) -> dict:
    """Update paper trading settings."""
    if capital is not None:
        _settings["capital"] = capital
    if lot_sizes:
        _settings["lot_sizes"].update(lot_sizes)
    if max_sl_pct is not None:
        _settings["max_sl_pct"] = max_sl_pct
    _save_settings()
    return _settings


def get_settings() -> dict:
    return _settings.copy()


def open_position(strike: str, side: str, entry_price: float, lots: int,
                  index_id: str, reason: str, source: str = "SNIPER") -> dict:
    """Open a new paper trade position."""
    global _capital_used
    now = datetime.now(IST)
    lot_size = _settings["lot_sizes"].get(index_id, 75)
    sl_pct = _settings["max_sl_pct"] / 100
    capital_needed = entry_price * lot_size * lots

    if _capital_used + capital_needed > _settings["capital"]:
        return {"error": "Insufficient capital", "available": _settings["capital"] - _capital_used}

    position = {
        "id": f"PT{int(time.time())}",
        "strike": strike,
        "side": side,
        "index": index_id,
        "entry_price": round(entry_price, 1),
        "current_ltp": round(entry_price, 1),
        "stop_loss": round(entry_price * (1 - sl_pct), 1),
        "target1": round(entry_price * 1.30, 1),
        "target2": round(entry_price * 1.60, 1),
        "lots": lots,
        "lot_size": lot_size,
        "quantity": lots * lot_size,
        "capital_used": round(capital_needed, 0),
        "entry_time": now.isoformat(),
        "pnl_pct": 0,
        "pnl_abs": 0,
        "peak_pnl": 0,
        "status": "OPEN",
        "reason": reason[:200],
        "source": source,
        "ltp_history": [{"time": now.strftime("%H:%M:%S"), "ltp": entry_price}],
    }

    _positions.append(position)
    _capital_used += capital_needed
    return position


def update_positions(chain: dict) -> list[dict]:
    """Update all active positions with live LTP. Returns list of closed positions."""
    global _capital_used
    now = datetime.now(IST)
    closed = []

    for pos in _positions[:]:
        strike_num = int(pos["strike"].split()[0])
        side = pos["side"]
        info = chain.get(strike_num, {}).get(side, {})
        current_ltp = info.get("last_price", 0) if info else 0

        if current_ltp <= 0:
            continue

        entry = pos["entry_price"]
        pnl_pct = (current_ltp - entry) / entry * 100
        pnl_abs = (current_ltp - entry) * pos["quantity"]

        pos["current_ltp"] = round(current_ltp, 1)
        pos["pnl_pct"] = round(pnl_pct, 1)
        pos["pnl_abs"] = round(pnl_abs, 0)
        pos["peak_pnl"] = max(pos.get("peak_pnl", 0), pnl_pct)

        # Track LTP history (last 100 ticks)
        if len(pos["ltp_history"]) < 100:
            pos["ltp_history"].append({"time": now.strftime("%H:%M:%S"), "ltp": current_ltp})

        exit_reason = ""

        # SL Hit
        if current_ltp <= pos["stop_loss"]:
            exit_reason = "SL HIT"
        # T1 Hit
        elif current_ltp >= pos["target1"] and not pos.get("t1_hit"):
            pos["t1_hit"] = True
            # Trail SL to breakeven + 5%
            pos["stop_loss"] = round(entry * 1.05, 1)
        # T2 Hit
        elif current_ltp >= pos["target2"]:
            exit_reason = "T2 HIT"
        # Time stop: market close
        elif now.hour == 15 and now.minute >= 20:
            exit_reason = "MARKET CLOSE"

        if exit_reason:
            pos["exit_price"] = round(current_ltp, 1)
            pos["exit_time"] = now.isoformat()
            pos["exit_reason"] = exit_reason
            pos["status"] = "CLOSED"
            pos["final_pnl_pct"] = round(pnl_pct, 1)
            pos["final_pnl_abs"] = round(pnl_abs, 0)
            pos["hold_time_min"] = round((now - datetime.fromisoformat(pos["entry_time"])).total_seconds() / 60, 1)

            _capital_used -= pos["capital_used"]
            _positions.remove(pos)
            _closed_today.append(pos)
            _save_day_trades(_today(), _closed_today)
            closed.append(pos)

    # Track equity curve
    total_open_pnl = sum(p["pnl_abs"] for p in _positions)
    total_closed_pnl = sum(t.get("final_pnl_abs", 0) for t in _closed_today)
    equity = _settings["capital"] + total_closed_pnl + total_open_pnl
    _pnl_history.append((time.time(), equity))

    return closed


def auto_fetch_signal(sniper: dict, command: dict) -> dict | None:
    """Auto-fetch trade from Sniper or Command Center."""
    global _last_auto_fetch_ts
    now_ts = time.time()

    if now_ts - _last_auto_fetch_ts < AUTO_FETCH_COOLDOWN:
        return None

    # Don't open if already at max positions
    if len(_positions) >= _settings["max_positions"]:
        return None

    # Priority 1: Sniper SCOUT entry
    sniper_pos = sniper.get("position")
    if sniper_pos and sniper.get("phase") == "SCOUT":
        strike = sniper_pos.get("strike", "")
        side = sniper_pos.get("side", "")
        entry = sniper_pos.get("avg_entry", 0)
        if strike and entry > 0 and not _has_position(strike):
            _last_auto_fetch_ts = now_ts
            index = sniper_pos.get("index", "NIFTY") if "index" in sniper_pos else (
                "BANKNIFTY" if "BANK" in strike else "SENSEX" if "SENSEX" in strike else "NIFTY"
            )
            return open_position(
                strike=strike, side=side, entry_price=entry, lots=1,
                index_id=index, reason=f"Sniper SCOUT: {', '.join(sniper.get('reasons', [])[:2])}",
                source="SNIPER",
            )

    # Priority 2: Command Center BUY
    cmd_trade = command.get("trade")
    cmd_signal = command.get("signal", "")
    if cmd_trade and cmd_signal in ("BUY", "STRONG BUY"):
        strike = cmd_trade.get("strike", "")
        side = cmd_trade.get("side", "")
        entry = cmd_trade.get("entry", 0)
        if strike and entry > 0 and not _has_position(strike):
            _last_auto_fetch_ts = now_ts
            lots = cmd_trade.get("lots", 1)
            return open_position(
                strike=strike, side=side, entry_price=entry, lots=lots,
                index_id="NIFTY", reason=f"Command: {command.get('reason', '')[:100]}",
                source="COMMAND",
            )

    return None


def _has_position(strike: str) -> bool:
    return any(p["strike"] == strike for p in _positions)


def get_state(chain: dict = None) -> dict:
    """Full paper trading state for frontend."""
    # Update positions if chain provided
    closed_this_cycle = []
    if chain:
        closed_this_cycle = update_positions(chain)

    total_open_pnl = sum(p["pnl_abs"] for p in _positions)
    total_closed_pnl = sum(t.get("final_pnl_abs", 0) for t in _closed_today)
    total_pnl = total_open_pnl + total_closed_pnl
    equity = _settings["capital"] + total_pnl

    wins = [t for t in _closed_today if t.get("final_pnl_pct", 0) > 0]
    losses = [t for t in _closed_today if t.get("final_pnl_pct", 0) <= 0]

    # Equity curve (last 100 points)
    curve = [{"ts": p[0], "equity": round(p[1], 0)} for p in list(_pnl_history)[-100:]]

    return {
        "settings": _settings,
        "positions": _positions,
        "positions_count": len(_positions),
        "capital_total": _settings["capital"],
        "capital_used": round(_capital_used, 0),
        "capital_available": round(_settings["capital"] - _capital_used, 0),
        "equity": round(equity, 0),
        "total_pnl": round(total_pnl, 0),
        "total_pnl_pct": round(total_pnl / _settings["capital"] * 100, 2),
        "open_pnl": round(total_open_pnl, 0),
        "closed_pnl": round(total_closed_pnl, 0),
        "trades_today": len(_closed_today),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / max(len(_closed_today), 1) * 100, 1),
        "best_trade": max(_closed_today, key=lambda t: t.get("final_pnl_pct", 0), default=None),
        "worst_trade": min(_closed_today, key=lambda t: t.get("final_pnl_pct", 0), default=None),
        "closed_trades": _closed_today[-10:],
        "just_closed": closed_this_cycle,
        "equity_curve": curve,
        "timestamp": datetime.now(IST).isoformat(),
    }


def get_report(period: str = "daily") -> dict:
    """Generate detailed P&L report — real math, no mock."""
    today = datetime.now(IST)
    starting_capital = _settings.get("starting_capital", _settings["capital"])

    if period == "daily":
        dates = [_today()]
    elif period == "weekly":
        dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    else:
        dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(31)]

    all_trades = []
    daily_pnls = []
    for date in dates:
        trades = _load_day_trades(date)
        if trades:
            day_wins = [t for t in trades if (t.get("final_pnl_abs", 0)) > 0]
            day_losses = [t for t in trades if (t.get("final_pnl_abs", 0)) <= 0]
            day_gross_profit = sum(t.get("final_pnl_abs", 0) for t in day_wins)
            day_gross_loss = sum(t.get("final_pnl_abs", 0) for t in day_losses)
            day_net = day_gross_profit + day_gross_loss
            day_capital_used = sum(t.get("capital_used", 0) for t in trades)

            daily_pnls.append({
                "date": date,
                "trades": len(trades),
                "wins": len(day_wins),
                "losses": len(day_losses),
                "gross_profit": round(day_gross_profit, 0),
                "gross_loss": round(day_gross_loss, 0),
                "net_pnl": round(day_net, 0),
                "capital_used": round(day_capital_used, 0),
                "win_rate": round(len(day_wins) / max(len(trades), 1) * 100, 1),
            })
            all_trades.extend(trades)

    # ── Full math ──
    total_trades = len(all_trades)
    wins = [t for t in all_trades if (t.get("final_pnl_abs", 0)) > 0]
    losses = [t for t in all_trades if (t.get("final_pnl_abs", 0)) <= 0]
    gross_profit = sum(t.get("final_pnl_abs", 0) for t in wins)
    gross_loss = sum(t.get("final_pnl_abs", 0) for t in losses)  # negative number
    net_pnl = gross_profit + gross_loss
    total_capital_used = sum(t.get("capital_used", 0) for t in all_trades)

    # Capital tracking
    capital_after = starting_capital + net_pnl
    capital_growth_pct = round(net_pnl / starting_capital * 100, 2) if starting_capital > 0 else 0
    capital_remaining = round(capital_after, 0)

    # Avg win / avg loss
    avg_win = round(sum(t.get("final_pnl_abs", 0) for t in wins) / max(len(wins), 1), 0)
    avg_loss = round(sum(t.get("final_pnl_abs", 0) for t in losses) / max(len(losses), 1), 0)
    avg_win_pct = round(sum(t.get("final_pnl_pct", 0) for t in wins) / max(len(wins), 1), 1)
    avg_loss_pct = round(sum(t.get("final_pnl_pct", 0) for t in losses) / max(len(losses), 1), 1)

    # Profit factor
    profit_factor = round(abs(gross_profit) / abs(gross_loss), 2) if gross_loss != 0 else 999

    # Max drawdown
    running = 0
    peak = 0
    max_dd = 0
    for t in all_trades:
        running += t.get("final_pnl_abs", 0)
        if running > peak:
            peak = running
        dd = peak - running
        if dd > max_dd:
            max_dd = dd

    # Expectancy = (win_rate × avg_win) + (loss_rate × avg_loss)
    wr = len(wins) / max(total_trades, 1)
    expectancy = round(wr * avg_win + (1 - wr) * avg_loss, 0)

    # Best/worst streaks
    max_win_streak = max_loss_streak = curr = 0
    for t in all_trades:
        pnl = t.get("final_pnl_abs", 0)
        if pnl > 0:
            curr = curr + 1 if curr > 0 else 1
            max_win_streak = max(max_win_streak, curr)
        else:
            curr = curr - 1 if curr < 0 else -1
            max_loss_streak = max(max_loss_streak, abs(curr))

    return {
        "period": period,
        "period_label": "Today" if period == "daily" else "Last 7 Days" if period == "weekly" else "This Month",

        # Trade counts
        "total_trades": total_trades,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / max(total_trades, 1) * 100, 1),

        # P&L — real math
        "gross_profit": round(gross_profit, 0),
        "gross_loss": round(gross_loss, 0),
        "net_pnl": round(net_pnl, 0),
        "net_pnl_pct": capital_growth_pct,
        "profit_factor": profit_factor,
        "expectancy": expectancy,

        # Averages
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "avg_win_pct": avg_win_pct,
        "avg_loss_pct": avg_loss_pct,

        # Capital
        "starting_capital": starting_capital,
        "capital_used_total": round(total_capital_used, 0),
        "capital_remaining": capital_remaining,
        "capital_growth": round(net_pnl, 0),
        "capital_growth_pct": capital_growth_pct,

        # Risk
        "max_drawdown": round(max_dd, 0),
        "max_drawdown_pct": round(max_dd / starting_capital * 100, 2) if starting_capital > 0 else 0,
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,

        # Daily breakdown
        "daily_pnls": daily_pnls,

        # Trades
        "trades": all_trades[-20:],

        # Lot sizes (for reference)
        "lot_sizes": _settings["lot_sizes"],
    }
