"""Persistent Data Store — JSON file-based storage for daily snapshots, signals, levels.

Saves to ./data/ directory. On Render with persistent disk, survives restarts.
Locally, saves in the backend directory.
"""

import json
import os
from datetime import datetime, timedelta

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))


def _ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


class DataStore:
    """JSON file persistence for market data."""

    def __init__(self):
        os.makedirs(os.path.join(DATA_DIR, "daily"), exist_ok=True)
        os.makedirs(os.path.join(DATA_DIR, "signals"), exist_ok=True)
        os.makedirs(os.path.join(DATA_DIR, "levels"), exist_ok=True)
        print(f"[STORE] Data directory: {DATA_DIR}")

    # --- Daily Snapshots ---

    def save_daily_snapshot(self, date: str, index: str, data: dict):
        """Save daily snapshot (OI, support/resistance, OHLC, etc.)."""
        path = os.path.join(DATA_DIR, "daily", f"{date}_{index}.json")
        _ensure_dir(path)
        # Merge with existing data if present
        existing = self.load_daily_snapshot(date, index)
        existing.update(data)
        existing["date"] = date
        existing["index"] = index
        existing["saved_at"] = datetime.now().isoformat()
        with open(path, "w") as f:
            json.dump(existing, f, indent=2, default=str)
        print(f"[STORE] Saved daily snapshot: {date} {index}")

    def load_daily_snapshot(self, date: str, index: str) -> dict:
        """Load daily snapshot."""
        path = os.path.join(DATA_DIR, "daily", f"{date}_{index}.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}

    def get_daily_history(self, index: str, days: int = 30) -> list[dict]:
        """Load last N days of snapshots."""
        results = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            snap = self.load_daily_snapshot(date, index)
            if snap:
                results.append(snap)
        return results

    # --- Signal History ---

    def save_signals(self, date: str, signals: list[dict]):
        """Save all signals for a date."""
        path = os.path.join(DATA_DIR, "signals", f"{date}_signals.json")
        _ensure_dir(path)
        with open(path, "w") as f:
            json.dump({"date": date, "signals": signals, "saved_at": datetime.now().isoformat()}, f, indent=2, default=str)

    def load_signals(self, date: str) -> list[dict]:
        """Load signals for a date."""
        path = os.path.join(DATA_DIR, "signals", f"{date}_signals.json")
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
                return data.get("signals", [])
        return []

    def append_signal(self, signal: dict):
        """Append a single signal to today's file."""
        date = datetime.now().strftime("%Y-%m-%d")
        existing = self.load_signals(date)
        existing.append(signal)
        self.save_signals(date, existing)

    # --- Key Levels (persisted support/resistance/breakouts) ---

    def save_levels(self, index: str, levels: dict):
        """Save key levels (support, resistance, breakouts) for an index."""
        path = os.path.join(DATA_DIR, "levels", f"{index}_levels.json")
        _ensure_dir(path)
        levels["updated_at"] = datetime.now().isoformat()
        with open(path, "w") as f:
            json.dump(levels, f, indent=2, default=str)

    def load_levels(self, index: str) -> dict:
        """Load key levels for an index."""
        path = os.path.join(DATA_DIR, "levels", f"{index}_levels.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}

    # --- Auto Save (called every 30 min during market hours) ---

    def auto_save(self, index: str, spot: float, atm: int, chain_summary: list,
                  supports: list, resistances: list, trend_data: dict,
                  confluence: dict, signals: list):
        """Auto-save current state as daily snapshot."""
        date = datetime.now().strftime("%Y-%m-%d")
        now = datetime.now()

        # Only save during market hours (9:15 - 15:30 IST)
        if now.hour < 9 or (now.hour == 9 and now.minute < 15) or now.hour >= 16:
            return

        # Build OI snapshot from chain
        oi_snapshot = {}
        for row in chain_summary:
            strike = row.get("strike", 0)
            oi_snapshot[str(strike)] = {
                "ce_oi": row.get("ce_oi", 0),
                "pe_oi": row.get("pe_oi", 0),
                "ce_oi_chg": row.get("ce_oi_chg", 0),
                "pe_oi_chg": row.get("pe_oi_chg", 0),
                "ce_vol": row.get("ce_vol", 0),
                "pe_vol": row.get("pe_vol", 0),
                "ce_iv": row.get("ce_iv", 0),
                "pe_iv": row.get("pe_iv", 0),
            }

        # Find max OI strikes
        max_ce_oi_strike = max(chain_summary, key=lambda r: r.get("ce_oi", 0), default={}).get("strike", 0) if chain_summary else 0
        max_pe_oi_strike = max(chain_summary, key=lambda r: r.get("pe_oi", 0), default={}).get("strike", 0) if chain_summary else 0

        snapshot = {
            "spot": spot,
            "atm": atm,
            "time": now.isoformat(),
            "open": trend_data.get("today_open", 0),
            "high": trend_data.get("today_high", 0),
            "low": trend_data.get("today_low", 0),
            "prev_close": trend_data.get("prev_close", 0),
            "gap": trend_data.get("gap", 0),
            "gap_pct": trend_data.get("gap_pct", 0),
            "gap_type": trend_data.get("gap_type", ""),
            "supports": supports,
            "resistances": resistances,
            "max_ce_oi_strike": max_ce_oi_strike,
            "max_pe_oi_strike": max_pe_oi_strike,
            "confluence_score": confluence.get("score", 0),
            "confluence_direction": confluence.get("direction", ""),
            "oi_snapshot": oi_snapshot,
        }

        self.save_daily_snapshot(date, index, snapshot)

        # Also save signals
        if signals:
            self.save_signals(date, signals)

        # Save key levels
        self.save_levels(index, {
            "supports": supports,
            "resistances": resistances,
            "max_ce_oi": max_ce_oi_strike,
            "max_pe_oi": max_pe_oi_strike,
            "spot": spot,
            "atm": atm,
        })
