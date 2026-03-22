"""Data Aggregator v2 — Multi-index (Nifty/BankNifty/Sensex), caching, flow tape."""
import asyncio
import time
from datetime import datetime
from kite_client import KiteClient
from detectors import ALL_DETECTORS
from confluence_engine import calculate
from brain_signal import generate

INDICES = {
    "NIFTY": {"symbol": "NSE:NIFTY 50", "name": "NIFTY", "strike_step": 50, "range": 500, "lot": 25},
    "BANKNIFTY": {"symbol": "NSE:NIFTY BANK", "name": "BANKNIFTY", "strike_step": 100, "range": 1000, "lot": 15},
    "SENSEX": {"symbol": "BSE:SENSEX", "name": "SENSEX", "strike_step": 100, "range": 1500, "lot": 10},
}


class IndexState:
    """State for one index."""
    def __init__(self, index_id: str):
        self.index_id = index_id
        self.cfg = INDICES[index_id]
        self.spot = 0.0
        self.atm = 0
        self.chain: dict = {}
        self.detectors: dict = {}
        self.confluence: dict = {"score": 0, "status": "NEUTRAL", "color": "grey", "direction": "NEUTRAL",
                                  "time_multiplier": 1, "is_expiry_day": False, "breakdown": {}, "firing": [], "timestamp": ""}
        self.brain: dict = {"active": False, "score": 0, "direction": "NEUTRAL", "primary": None, "secondary": None, "exit_rules": [], "firing": []}
        self.strike_map: list = []
        self.raw_data: dict = {}
        self.error: str = ""
        self.last_fetch: float = 0

    def to_dict(self) -> dict:
        return {
            "index_id": self.index_id,
            "name": self.cfg["name"],
            "spot": self.spot,
            "atm": self.atm,
            "detectors": self.detectors,
            "confluence": self.confluence,
            "brain": self.brain,
            "strike_map": self.strike_map,
            "chain_summary": self._chain_summary(),
            "error": self.error,
            "last_fetch": self.last_fetch,
        }

    def _chain_summary(self) -> list:
        """Summarized chain for frontend strike detail."""
        rows = []
        for strike in sorted(self.chain.keys()):
            s = self.chain[strike]
            ce = s.get("CE") or {}
            pe = s.get("PE") or {}
            rows.append({
                "strike": strike,
                "ce_ltp": ce.get("last_price", 0), "ce_vol": ce.get("volume", 0),
                "ce_oi": ce.get("oi", 0), "ce_iv": ce.get("iv", 0),
                "ce_bid": ce.get("bid", 0), "ce_ask": ce.get("ask", 0),
                "ce_oi_chg": ce.get("oi_day_change", 0),
                "pe_ltp": pe.get("last_price", 0), "pe_vol": pe.get("volume", 0),
                "pe_oi": pe.get("oi", 0), "pe_iv": pe.get("iv", 0),
                "pe_bid": pe.get("bid", 0), "pe_ask": pe.get("ask", 0),
                "pe_oi_chg": pe.get("oi_day_change", 0),
                "is_atm": abs(strike - self.atm) < self.cfg["strike_step"] / 2,
            })
        return rows


class UserAggregator:
    """Multi-index aggregator per user session."""

    def __init__(self, kite: KiteClient):
        self.kite = kite
        self.indices: dict[str, IndexState] = {k: IndexState(k) for k in INDICES}
        self.active_index = "NIFTY"
        self.alert_log: list[dict] = []
        self.flow_tape: list[dict] = []  # options flow tape
        self._prev_scores: dict[str, float] = {}
        self._cache: dict[str, tuple[float, dict]] = {}  # key -> (time, data)
        self._spot_cache: dict[str, tuple[float, float]] = {}  # symbol -> (time, price)

    async def _get_spot_cached(self, symbol: str, ttl: float = 5) -> float:
        """Cache spot prices for `ttl` seconds."""
        now = time.time()
        if symbol in self._spot_cache:
            ts, price = self._spot_cache[symbol]
            if now - ts < ttl and price > 0:
                return price
        try:
            data = await self.kite.get_ltp([symbol])
            price = list(data.values())[0].get("last_price", 0) if data else 0
            if price > 0:
                self._spot_cache[symbol] = (now, price)
            return price
        except Exception:
            return self._spot_cache.get(symbol, (0, 0))[1]

    async def _build_chain_cached(self, index_id: str, spot: float, ttl: float = 25) -> dict:
        """Cache option chain for `ttl` seconds."""
        now = time.time()
        key = f"chain_{index_id}"
        if key in self._cache:
            ts, data = self._cache[key]
            if now - ts < ttl:
                return data
        cfg = INDICES[index_id]
        data = await self.kite.build_option_chain(spot, name=cfg["name"], strike_step=cfg["strike_step"], chain_range=cfg["range"])
        self._cache[key] = (now, data)
        return data

    async def run_cycle(self, index_id: str | None = None) -> dict:
        """Run detectors for specified index (or all)."""
        targets = [index_id] if index_id else list(INDICES.keys())

        # Fetch all spots in parallel
        spots = {}
        for idx in targets:
            cfg = INDICES[idx]
            try:
                spots[idx] = await self._get_spot_cached(cfg["symbol"])
            except Exception:
                spots[idx] = 0

        # Build chains + run detectors for each index
        for idx in targets:
            state = self.indices[idx]
            spot = spots.get(idx, 0)
            if spot <= 0:
                state.error = f"Could not fetch {idx} price"
                continue

            state.spot = spot
            try:
                chain_data = await self._build_chain_cached(idx, spot)
                state.atm = chain_data.get("atm", 0)
                state.chain = chain_data.get("chain", {})

                # Build detector input
                raw = {
                    "spot": spot, "atm": state.atm, "chain": state.chain,
                    "trade_log": [], "sweep_events": [], "skew_history": [],
                    "banknifty": {"nifty_change_pct": 0, "expected_bn_change_pct": 0, "actual_bn_change_pct": 0},
                    "fii_dii": {"fii_net_cr": 0, "dii_net_cr": 0},
                    "max_pain": state.atm, "depth_map": {},
                    "expiry_date": chain_data.get("expiry", ""),
                    "is_expiry_day": False, "time_to_expiry_mins": 1440,
                    "trend": 0, "timestamp": datetime.now().isoformat(),
                }

                # Max pain
                strikes_list = sorted(state.chain.keys())
                if strikes_list:
                    mp_losses = {}
                    for mp in strikes_list:
                        loss = 0
                        for s in strikes_list:
                            ce = state.chain[s].get("CE")
                            pe = state.chain[s].get("PE")
                            if mp > s and ce: loss += (mp - s) * ce.get("oi", 0)
                            elif mp < s and pe: loss += (s - mp) * pe.get("oi", 0)
                        mp_losses[mp] = loss
                    if mp_losses:
                        raw["max_pain"] = min(mp_losses, key=mp_losses.get)

                    for s in strikes_list:
                        ce = state.chain[s].get("CE") or {}
                        pe = state.chain[s].get("PE") or {}
                        raw["depth_map"][s] = {
                            "CE": ce.get("bid_qty", 0) + ce.get("ask_qty", 0),
                            "PE": pe.get("bid_qty", 0) + pe.get("ask_qty", 0),
                        }

                state.raw_data = raw

                # Run all 17 detectors
                state.detectors = {}
                for det_id, fn in ALL_DETECTORS.items():
                    try:
                        state.detectors[det_id] = fn(raw)
                    except Exception:
                        state.detectors[det_id] = {"id": det_id, "name": det_id, "score": 0, "status": "NORMAL", "metric": "Error", "alerts": []}

                state.confluence = calculate(state.detectors, is_expiry_day=raw.get("is_expiry_day", False))
                state.brain = generate(state.confluence, state.detectors, raw)
                state.strike_map = state.detectors.get("d06_confluence_map", {}).get("strike_map", [])

                # Alerts
                score = state.confluence.get("score", 0)
                prev = self._prev_scores.get(idx, 0)
                if score >= 76 and prev < 76:
                    self.alert_log.append({"type": "SIGNAL", "time": datetime.now().isoformat(),
                                           "message": f"[{idx}] CONFLUENCE {state.confluence['status']} — Score {score:.0f} — {state.confluence['direction']}"})
                for det_id, result in state.detectors.items():
                    if result.get("status") in ("CRITICAL", "ALERT"):
                        for a in result.get("alerts", [])[:1]:
                            self.alert_log.append({"type": result["status"], "time": datetime.now().isoformat(),
                                                    "message": f"[{idx}] {result.get('name', det_id)} — {result.get('metric', '')}"})
                self._prev_scores[idx] = score
                state.error = ""
                state.last_fetch = time.time()

                # Build flow tape entries from chain volume
                for strike in strikes_list[:10]:  # top strikes
                    for side in ("CE", "PE"):
                        info = state.chain[strike].get(side)
                        if info and info.get("volume", 0) > 500:
                            self.flow_tape.append({
                                "time": datetime.now().isoformat(),
                                "index": idx,
                                "strike": f"{int(strike)} {side}",
                                "price": info["last_price"],
                                "volume": info["volume"],
                                "oi": info["oi"],
                                "type": "BUY" if info.get("buy_pct", 0.5) > 0.6 else "SELL" if info.get("buy_pct", 0.5) < 0.4 else "NEUTRAL",
                            })

            except Exception as e:
                state.error = str(e)[:200]

        self.alert_log = self.alert_log[-200:]
        self.flow_tape = self.flow_tape[-100:]
        return self.get_state()

    def get_state(self) -> dict:
        return {
            "active_index": self.active_index,
            "indices": {k: v.to_dict() for k, v in self.indices.items()},
            "spots": {k: v.spot for k, v in self.indices.items()},
            "alert_log": self.alert_log[-30:],
            "flow_tape": self.flow_tape[-50:],
            "timestamp": datetime.now().isoformat(),
            # Active index shortcut fields (backward compat)
            "spot": self.indices[self.active_index].spot,
            "atm": self.indices[self.active_index].atm,
            "detectors": self.indices[self.active_index].detectors,
            "confluence": self.indices[self.active_index].confluence,
            "brain": self.indices[self.active_index].brain,
            "strike_map": self.indices[self.active_index].strike_map,
            "chain_summary": self.indices[self.active_index]._chain_summary(),
            "error": self.indices[self.active_index].error,
        }


user_aggregators: dict[str, UserAggregator] = {}

def get_or_create_aggregator(session_id: str, kite: KiteClient) -> UserAggregator:
    if session_id not in user_aggregators:
        user_aggregators[session_id] = UserAggregator(kite)
    return user_aggregators[session_id]

def remove_aggregator(session_id: str):
    user_aggregators.pop(session_id, None)
