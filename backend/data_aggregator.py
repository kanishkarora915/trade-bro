"""Data Aggregator v3.1 — Multi-index with real tick data, FII/DII, AI analysis, India VIX.

Fixes: Non-blocking FII/DII fetch, only active index per cycle, India VIX support.
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from kite_client import KiteClient

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

def now_ist() -> datetime:
    """Get current time in IST."""
    return datetime.now(IST)

def now_ist_iso() -> str:
    """Get current time in IST as ISO string."""
    return now_ist().isoformat()
from kite_ticker import KiteTicker
from nse_scraper import fetch_fii_dii
from ai_analyst import generate_analysis
from detectors import ALL_DETECTORS
from check_trades_engine import analyze_setups
from confluence_engine import calculate
from brain_signal import generate
from bob_engine import generate as bob_generate
from timeframe_engine import TimeframeEngine
from data_store import DataStore
from mtf_analyzer import analyze_mtf

INDICES = {
    "NIFTY": {"symbol": "NSE:NIFTY 50", "name": "NIFTY", "strike_step": 50, "range": 500, "lot": 25},
    "BANKNIFTY": {"symbol": "NSE:NIFTY BANK", "name": "BANKNIFTY", "strike_step": 100, "range": 1000, "lot": 15},
    "SENSEX": {"symbol": "BSE:SENSEX", "name": "SENSEX", "strike_step": 100, "range": 1000, "lot": 10},
}

VIX_SYMBOL = "NSE:INDIA VIX"


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
        self.bob_signal: dict = {"signal": "WAIT", "reason": "Initializing...", "gates": {}, "confluence_score": 0}
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
                "ce_buy_pct": ce.get("buy_pct", 0.5),
                "ce_buy_qty": ce.get("buy_quantity", 0), "ce_sell_qty": ce.get("sell_quantity", 0),
                "ce_chg": ce.get("net_change", 0),
                "pe_ltp": pe.get("last_price", 0), "pe_vol": pe.get("volume", 0),
                "pe_oi": pe.get("oi", 0), "pe_iv": pe.get("iv", 0),
                "pe_bid": pe.get("bid", 0), "pe_ask": pe.get("ask", 0),
                "pe_oi_chg": pe.get("oi_day_change", 0),
                "pe_buy_pct": pe.get("buy_pct", 0.5),
                "pe_buy_qty": pe.get("buy_quantity", 0), "pe_sell_qty": pe.get("sell_quantity", 0),
                "pe_chg": pe.get("net_change", 0),
                "is_atm": abs(strike - self.atm) < self.cfg["strike_step"] / 2,
            })
        return rows


class UserAggregator:
    """Multi-index aggregator per user session."""

    def __init__(self, kite: KiteClient, ticker: KiteTicker | None = None):
        self.kite = kite
        self.ticker = ticker
        self.indices: dict[str, IndexState] = {k: IndexState(k) for k in INDICES}
        self.active_index = "NIFTY"
        self.alert_log: list[dict] = []
        self.flow_tape: list[dict] = []
        self.ai_analysis: dict = {}
        self.fii_dii: dict = {}
        self.india_vix: float = 0.0
        self.vix_enabled: bool = True  # VIX integration toggle
        self.check_trades: list = []  # MTF + OI trade setups
        self.tf_engine = TimeframeEngine(kite)
        self.data_store = DataStore()
        # Load persisted signals from disk (survives restarts!)
        today = now_ist().strftime("%Y-%m-%d")
        self.signal_history: list[dict] = self.data_store.load_signals(today)
        self.last_signal: dict | None = self.signal_history[-1] if self.signal_history else None
        print(f"[AGG] Loaded {len(self.signal_history)} signals from disk for {today}")
        self.mtf_analysis: dict = {}
        self._last_tf_short: float = 0  # last short TF refresh
        self._last_tf_long: float = 0   # last long TF refresh
        self._last_auto_save: float = 0 # last auto-save
        self.selected_expiry: str | None = None  # user-selected expiry (None = nearest)
        self.skew_history: dict[str, list[dict]] = {k: [] for k in INDICES}
        # Gap & Trend tracking
        self.trend_data: dict[str, dict] = {}  # per-index trend info
        self._spot_history: dict[str, list[tuple[float, float]]] = {k: [] for k in INDICES}  # (timestamp, price)
        self._prev_scores: dict[str, float] = {}
        self._cache: dict[str, tuple[float, dict]] = {}
        self._spot_cache: dict[str, tuple[float, float]] = {}
        self._fii_dii_task: asyncio.Task | None = None

    async def _get_spot_cached(self, symbol: str, ttl: float = 5) -> float:
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

    async def _fetch_vix(self) -> float:
        """Fetch India VIX value."""
        try:
            data = await self.kite.get_ltp([VIX_SYMBOL])
            vix = list(data.values())[0].get("last_price", 0) if data else 0
            if vix > 0:
                self.india_vix = vix
            return self.india_vix
        except Exception:
            return self.india_vix

    async def _build_chain_cached(self, index_id: str, spot: float, ttl: float = 4) -> dict:
        now = time.time()
        key = f"chain_{index_id}"
        if key in self._cache:
            ts, data = self._cache[key]
            if now - ts < ttl:
                return data
        cfg = INDICES[index_id]
        data = await self.kite.build_option_chain(
            spot, expiry=self.selected_expiry,
            name=cfg["name"], strike_step=cfg["strike_step"], chain_range=cfg["range"]
        )
        self._cache[key] = (now, data)
        return data

    async def _subscribe_ticker(self, chain: dict, index_id: str):
        if not self.ticker or not self.ticker._running:
            return
        cfg = INDICES[index_id]
        new_tokens = self.ticker.register_tokens(chain, index_id, cfg["lot"])
        if new_tokens:
            try:
                await self.ticker.subscribe(new_tokens)
            except Exception as e:
                print(f"[AGG] Ticker subscribe error: {e}")

    def _enrich_chain_with_ticks(self, chain: dict, index_id: str):
        if not self.ticker:
            return
        flow = self.ticker.get_flow_for_chain(chain, index_id)
        for strike, sides in chain.items():
            if strike in flow:
                for side_key in ("CE", "PE"):
                    if side_key in flow[strike] and sides.get(side_key):
                        tick_flow = flow[strike][side_key]
                        sides[side_key]["buy_pct"] = tick_flow.get("buy_pct", 0.5)
                        if tick_flow.get("volume", 0) > 0:
                            sides[side_key]["volume"] = tick_flow["volume"]
                        if tick_flow.get("oi", 0) > 0:
                            sides[side_key]["oi"] = tick_flow["oi"]

    def _start_fii_dii_background(self):
        """Start FII/DII fetch as background task (non-blocking)."""
        if self._fii_dii_task and not self._fii_dii_task.done():
            return  # already running

        async def _fetch():
            try:
                data = await fetch_fii_dii()
                if data:
                    self.fii_dii = data
            except Exception as e:
                print(f"[AGG] FII/DII background fetch error: {e}")

        self._fii_dii_task = asyncio.create_task(_fetch())

    async def _calculate_trend(self, spots: dict, targets: list):
        """Calculate gap up/down + intraday trend for each index."""
        now = time.time()
        for idx in INDICES:
            spot = spots.get(idx, 0)
            if spot <= 0:
                continue

            # Track spot history (keep last 60 data points ~30 min at 30s intervals)
            self._spot_history[idx].append((now, spot))
            self._spot_history[idx] = self._spot_history[idx][-60:]

            # Get OHLC data from Kite (previous close, today's open/high/low)
            if idx not in self.trend_data or now - self.trend_data[idx].get("_ts", 0) > 120:
                try:
                    sym = INDICES[idx]["symbol"]
                    quote = await self.kite.get_quote([sym])
                    q = quote.get(sym, {})
                    ohlc = q.get("ohlc", {})
                    prev_close = ohlc.get("close", 0)
                    today_open = ohlc.get("open", 0)
                    today_high = ohlc.get("high", 0)
                    today_low = ohlc.get("low", 0)

                    gap = today_open - prev_close if prev_close > 0 else 0
                    gap_pct = (gap / prev_close * 100) if prev_close > 0 else 0
                    gap_type = "GAP UP" if gap_pct > 0.15 else "GAP DOWN" if gap_pct < -0.15 else "FLAT OPEN"

                    # Change from open
                    chg_from_open = spot - today_open if today_open > 0 else 0
                    chg_from_open_pct = (chg_from_open / today_open * 100) if today_open > 0 else 0

                    # Change from prev close
                    day_chg = spot - prev_close if prev_close > 0 else 0
                    day_chg_pct = (day_chg / prev_close * 100) if prev_close > 0 else 0

                    # Intraday range
                    day_range = today_high - today_low if today_high > 0 else 0

                    # Gap fill check
                    gap_filled = False
                    if gap > 0 and today_low <= prev_close:
                        gap_filled = True
                    elif gap < 0 and today_high >= prev_close:
                        gap_filled = True

                    # Trend from spot history (last 10 points = ~5 min)
                    history = self._spot_history[idx]
                    trend_dir = "SIDEWAYS"
                    trend_strength = 0
                    if len(history) >= 5:
                        recent = [p for _, p in history[-10:]]
                        first_half = sum(recent[:len(recent)//2]) / max(1, len(recent)//2)
                        second_half = sum(recent[len(recent)//2:]) / max(1, len(recent) - len(recent)//2)
                        diff = second_half - first_half
                        diff_pct = (diff / first_half * 100) if first_half > 0 else 0
                        if diff_pct > 0.05:
                            trend_dir = "TRENDING UP"
                            trend_strength = min(100, abs(diff_pct) * 30)
                        elif diff_pct < -0.05:
                            trend_dir = "TRENDING DOWN"
                            trend_strength = min(100, abs(diff_pct) * 30)
                        else:
                            trend_dir = "SIDEWAYS"
                            trend_strength = 0

                    # 5-min momentum
                    momentum_5m = 0
                    if len(history) >= 10:
                        old_price = history[-10][1]
                        momentum_5m = ((spot - old_price) / old_price * 100) if old_price > 0 else 0

                    self.trend_data[idx] = {
                        "prev_close": prev_close,
                        "today_open": today_open,
                        "today_high": today_high,
                        "today_low": today_low,
                        "gap": round(gap, 2),
                        "gap_pct": round(gap_pct, 2),
                        "gap_type": gap_type,
                        "gap_filled": gap_filled,
                        "day_chg": round(day_chg, 2),
                        "day_chg_pct": round(day_chg_pct, 2),
                        "chg_from_open": round(chg_from_open, 2),
                        "chg_from_open_pct": round(chg_from_open_pct, 2),
                        "day_range": round(day_range, 2),
                        "trend": trend_dir,
                        "trend_strength": round(trend_strength, 1),
                        "momentum_5m": round(momentum_5m, 3),
                        "spot_high": today_high,
                        "spot_low": today_low,
                        "_ts": now,
                    }
                except Exception as e:
                    print(f"[AGG] Trend calc error for {idx}: {e}")

    async def _refresh_timeframes(self, targets: list):
        """Refresh timeframe data at staggered intervals."""
        now = time.time()
        idx = self.active_index

        try:
            # Short timeframes: every 3 min
            if now - self._last_tf_short > 180:
                tf_data = await self.tf_engine.fetch_all(idx, short_only=True)
                self._last_tf_short = now

            # Long timeframes: every 15 min
            if now - self._last_tf_long > 900:
                tf_data = await self.tf_engine.fetch_all(idx, short_only=False)
                self._last_tf_long = now

            # Get all cached data and run MTF analysis
            all_tf = self.tf_engine.get_cached(idx)
            if all_tf:
                active = self.indices.get(idx)
                chain = active._chain_summary() if active else []
                self.mtf_analysis = analyze_mtf(all_tf, active.spot if active else 0, active.atm if active else 0, chain)

            # Auto-save every 30 min
            if now - self._last_auto_save > 1800:
                self._auto_save_snapshot()
                self._last_auto_save = now

        except Exception as e:
            print(f"[AGG] Timeframe error: {e}")

    def _auto_save_snapshot(self):
        """Auto-save current state to persistent storage."""
        try:
            idx = self.active_index
            active = self.indices.get(idx)
            if not active or active.spot <= 0:
                return

            chain = active._chain_summary()
            td = self.trend_data.get(idx, {})

            # Extract supports/resistances from MTF analysis
            supports = []
            resistances = []
            if self.mtf_analysis:
                kl = self.mtf_analysis.get("key_levels", {})
                supports = [{"level": v, "source": k} for k, v in kl.items() if "support" in k and v > 0]
                resistances = [{"level": v, "source": k} for k, v in kl.items() if "resistance" in k and v > 0]

            self.data_store.auto_save(
                index=idx,
                spot=active.spot,
                atm=active.atm,
                chain_summary=chain,
                supports=supports,
                resistances=resistances,
                trend_data=td,
                confluence=active.confluence,
                signals=self.signal_history,
            )
        except Exception as e:
            print(f"[AGG] Auto-save error: {e}")

    async def run_cycle(self, index_id: str | None = None) -> dict:
        """Run detectors for active index only (not all 3) for speed."""
        # Only run active index to avoid 3x API calls
        targets = [index_id] if index_id else [self.active_index]

        # NON-BLOCKING: FII/DII in background
        self._start_fii_dii_background()

        # PARALLEL FETCH: VIX + Spot prices + Chain build — all at once
        spots = {}
        all_symbols = [(idx, INDICES[idx]["symbol"]) for idx in INDICES]

        async def _fetch_spots():
            try:
                symbols_to_fetch = [s for _, s in all_symbols]
                data = await self.kite.get_ltp(symbols_to_fetch)
                for idx, sym in all_symbols:
                    price = data.get(sym, {}).get("last_price", 0)
                    if price > 0:
                        spots[idx] = price
                        self.indices[idx].spot = price
                        self._spot_cache[sym] = (time.time(), price)
            except Exception as e:
                print(f"[AGG] Spot fetch error: {e}")
                for idx in targets:
                    cfg = INDICES[idx]
                    spots[idx] = self._spot_cache.get(cfg["symbol"], (0, 0))[1]

        async def _fetch_vix_task():
            try:
                await self._fetch_vix()
            except Exception:
                pass

        # Run spots + VIX + timeframes in PARALLEL — saves ~400ms per cycle
        await asyncio.gather(
            _fetch_spots(),
            _fetch_vix_task(),
            self._refresh_timeframes(targets),
            return_exceptions=True,
        )

        # Trend calc (needs spots, so runs after)
        await self._calculate_trend(spots, targets)

        # Build chains + run detectors for target indices
        for idx in targets:
            state = self.indices[idx]
            spot = spots.get(idx, state.spot)
            if spot <= 0:
                state.error = f"Could not fetch {idx} price"
                continue

            state.spot = spot
            try:
                chain_data = await self._build_chain_cached(idx, spot)
                state.atm = chain_data.get("atm", 0)
                state.chain = chain_data.get("chain", {})

                # Record IV skew history for Skew Shift detector
                atm_data = state.chain.get(state.atm, {})
                ce_iv = (atm_data.get("CE") or {}).get("iv", 0)
                pe_iv = (atm_data.get("PE") or {}).get("iv", 0)
                if ce_iv > 0 and pe_iv > 0:
                    self.skew_history[idx].append({"ce_iv": ce_iv, "pe_iv": pe_iv, "ts": time.time()})
                    self.skew_history[idx] = self.skew_history[idx][-50:]  # keep last 50

                # Subscribe ticker (non-blocking, won't fail if ticker is off)
                await self._subscribe_ticker(state.chain, idx)

                # Enrich chain with real tick data
                self._enrich_chain_with_ticks(state.chain, idx)

                # Get real trade data from ticker
                trade_log = []
                sweep_events = []
                if self.ticker:
                    trade_log = self.ticker.get_trade_log(idx)
                    sweep_events = self.ticker.get_sweep_events(idx)

                # Build detector input with REAL data
                raw = {
                    "spot": spot, "atm": state.atm, "chain": state.chain,
                    "trade_log": trade_log,
                    "sweep_events": sweep_events,
                    "skew_history": self.skew_history.get(idx, []),
                    "banknifty": {"nifty_change_pct": 0, "expected_bn_change_pct": 0, "actual_bn_change_pct": 0},
                    "fii_dii": {
                        "fii_net_cr": self.fii_dii.get("fii_net_cr", 0),
                        "dii_net_cr": self.fii_dii.get("dii_net_cr", 0),
                    },
                    "max_pain": state.atm, "depth_map": {},
                    "expiry_date": chain_data.get("expiry", ""),
                    "is_expiry_day": False, "time_to_expiry_mins": 1440,
                    "trend": 0, "timestamp": now_ist_iso(),
                    # VIX data
                    "india_vix": self.india_vix,
                    "vix_enabled": self.vix_enabled,
                }

                # Check if today is expiry day
                today = datetime.now()
                expiry_str = chain_data.get("expiry", "")
                if expiry_str:
                    try:
                        expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                        if expiry_date == today.date():
                            raw["is_expiry_day"] = True
                            close_time = today.replace(hour=15, minute=30, second=0)
                            diff = (close_time - today).total_seconds() / 60
                            raw["time_to_expiry_mins"] = max(0, diff)
                    except ValueError:
                        pass

                # Cross-index correlation data
                if idx == "BANKNIFTY" and spots.get("NIFTY", 0) > 0:
                    nifty_spot = spots["NIFTY"]
                    nifty_state = self.indices.get("NIFTY")
                    nifty_close = nifty_spot  # fallback
                    if nifty_state and nifty_state.chain:
                        atm_data = nifty_state.chain.get(nifty_state.atm, {})
                        nifty_close = atm_data.get("CE", {}).get("close", nifty_spot) or nifty_spot
                    nifty_chg = ((nifty_spot - nifty_close) / nifty_close * 100) if nifty_close > 0 else 0
                    raw["banknifty"]["nifty_change_pct"] = nifty_chg
                    raw["banknifty"]["expected_bn_change_pct"] = nifty_chg * 1.5

                # Max pain calculation
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

                # VIX boost: when VIX > 20 and enabled, boost confluence score slightly
                if self.vix_enabled and self.india_vix > 20:
                    vix_mult = min(1.3, 1.0 + (self.india_vix - 20) / 50)
                    state.confluence["score"] = min(100, state.confluence["score"] * vix_mult)
                    state.confluence["vix_boost"] = round(vix_mult, 2)

                state.brain = generate(state.confluence, state.detectors, raw)

                # Bob the Buyer signal engine
                try:
                    state.bob_signal = bob_generate(
                        detectors=state.detectors, chain=state.chain,
                        spot=spot, atm=state.atm, india_vix=self.india_vix,
                        fii_dii=self.fii_dii,
                        time_to_expiry_mins=raw.get("time_to_expiry_mins", 60),
                        index_id=idx, lot_size=cfg["lot"], strike_step=cfg["strike_step"],
                        confluence_direction=state.confluence.get("direction", "NEUTRAL"),
                    )
                except Exception as e:
                    state.bob_signal = {"signal": "WAIT", "reason": f"Engine error: {e}", "gates": {}, "confluence_score": 0}

                state.strike_map = state.detectors.get("d06_confluence_map", {}).get("strike_map", [])

                # Signal history tracking — AGGRESSIVE + ACCURACY-GATED REPEATS
                if state.brain.get("active") and state.brain.get("primary"):
                    new_strike = state.brain["primary"].get("strike", "")
                    new_dir = state.brain.get("direction", "")
                    new_score = state.brain.get("score", 0)
                    now_ts = time.time()

                    firing_count = sum(1 for d in state.detectors.values() if d.get("status") in ("CRITICAL", "ALERT"))
                    # Original aggressive: just 1 detector firing is enough
                    quality_pass = firing_count >= 1

                    # Repeat signal logic: 5 min cooldown (was 15 min)
                    # Repeat only if accuracy > 90% on that strike
                    cooldown_ok = True
                    is_reentry = False
                    for prev in reversed(self.signal_history):
                        if (prev.get("primary", {}).get("strike") == new_strike
                                and prev.get("direction") == new_dir):
                            prev_time = prev.get("_ts", 0)
                            if now_ts - prev_time < 300:  # 5 min cooldown (was 15)
                                # Check accuracy: only repeat if win rate > 90% on this strike
                                strike_signals = [s for s in self.signal_history if s.get("primary", {}).get("strike") == new_strike]
                                wins = sum(1 for s in strike_signals if s.get("result") == "TARGET_HIT")
                                total = sum(1 for s in strike_signals if s.get("result") in ("TARGET_HIT", "SL_HIT"))
                                accuracy = (wins / total * 100) if total > 0 else 0
                                if accuracy < 90 or total == 0:
                                    cooldown_ok = False  # block repeat — accuracy too low
                                # else: allow repeat — 90%+ accuracy on this strike
                            elif now_ts - prev_time < 1800:  # within 30 min = re-entry
                                is_reentry = True
                            break

                    if quality_pass and cooldown_ok:
                        signal_entry = {
                            **state.brain,
                            "index": idx,
                            "recorded_at": now_ist_iso(),
                            "spot_at_signal": spot,
                            "firing_count": firing_count,
                            "is_reentry": is_reentry,
                            "_ts": now_ts,  # internal timestamp for cooldown
                        }
                        if is_reentry:
                            signal_entry["reentry_note"] = f"RE-ENTRY: Same setup as earlier, price now {state.brain['primary'].get('cmp', '?')}"

                        self.last_signal = signal_entry
                        self.signal_history.append(signal_entry)
                        self.signal_history = self.signal_history[-50:]
                        # Persist to disk
                        try:
                            self.data_store.append_signal(signal_entry)
                        except Exception:
                            pass

                # Alerts
                score = state.confluence.get("score", 0)
                prev = self._prev_scores.get(idx, 0)
                if score >= 76 and prev < 76:
                    self.alert_log.append({"type": "SIGNAL", "time": now_ist_iso(),
                                           "message": f"[{idx}] CONFLUENCE {state.confluence['status']} — Score {score:.0f} — {state.confluence['direction']}"})
                for det_id, result in state.detectors.items():
                    if result.get("status") in ("CRITICAL", "ALERT"):
                        for a in result.get("alerts", [])[:1]:
                            self.alert_log.append({"type": result["status"], "time": now_ist_iso(),
                                                    "message": f"[{idx}] {result.get('name', det_id)} — {result.get('metric', '')}"})
                self._prev_scores[idx] = score
                state.error = ""
                state.last_fetch = time.time()

                # Flow tape entries — smart BUY/SELL detection using OI + price + buy_pct
                for strike in strikes_list:
                    for side in ("CE", "PE"):
                        info = state.chain[strike].get(side)
                        if info and info.get("volume", 0) > 200:
                            bp = info.get("buy_pct", 0.5)
                            oi_chg = info.get("oi_day_change", 0)
                            net_chg = info.get("net_change", 0)
                            ltp = info.get("last_price", 0)

                            # Smart classification:
                            # 1. OI increasing + price rising = BUYING (new longs)
                            # 2. OI increasing + price falling = SELLING/WRITING (new shorts)
                            # 3. OI decreasing + price rising = SHORT COVERING (old shorts closing)
                            # 4. OI decreasing + price falling = LONG UNWINDING (old longs closing)
                            # Fallback to buy_pct if OI data unavailable
                            if oi_chg > 0 and net_chg < 0 and ltp > 0:
                                flow_type = "SELL"  # OI building + price falling = writing
                            elif oi_chg > 0 and net_chg >= 0:
                                flow_type = "BUY"   # OI building + price rising = fresh buying
                            elif bp > 0.55:
                                flow_type = "BUY"
                            elif bp < 0.45:
                                flow_type = "SELL"
                            else:
                                flow_type = "NEUTRAL"

                            self.flow_tape.append({
                                "time": now_ist_iso(),
                                "index": idx,
                                "strike": f"{int(strike)} {side}",
                                "side": side,
                                "price": ltp,
                                "volume": info["volume"],
                                "oi": info["oi"],
                                "oi_chg": oi_chg,
                                "net_chg": net_chg,
                                "buy_pct": round(bp * 100, 1),
                                "iv": info.get("iv", 0),
                                "type": flow_type,
                            })

            except Exception as e:
                state.error = str(e)[:200]
                print(f"[AGG] Error for {idx}: {e}")

        # Clear consumed ticker data
        if self.ticker:
            self.ticker.clear_consumed()

        # Track signal results (auto-train accuracy)
        self._track_signal_results()

        # AI analysis for active index
        active_state = self.indices[self.active_index]
        if active_state.detectors:
            try:
                self.ai_analysis = generate_analysis(
                    active_state.detectors,
                    active_state.confluence,
                    active_state.brain,
                    active_state.spot,
                    self.fii_dii,
                    self.active_index,
                )
            except Exception as e:
                self.ai_analysis = {"summary": "Analysis unavailable", "analysis": str(e)[:100],
                                     "bullets": [], "sentiment": "NEUTRAL", "confidence": "LOW",
                                     "risk_notes": [], "timestamp": now_ist_iso()}

        # Check Trades — MTF + OI explosion detection
        if active_state.chain:
            try:
                zone = self._analyze_zones()
                tf = self.tf_engine.get_cached(self.active_index)
                self.check_trades = analyze_setups(
                    chain=active_state.chain,
                    spot=active_state.spot,
                    atm=active_state.atm,
                    zone_analysis=zone,
                    tf_data=tf,
                    confluence=active_state.confluence,
                    detectors=active_state.detectors,
                    index_id=self.active_index,
                    strike_step=active_state.cfg["strike_step"],
                )
            except Exception as e:
                print(f"[AGG] Check trades error: {e}")

        self.alert_log = self.alert_log[-200:]
        self.flow_tape = self.flow_tape[-100:]
        return self.get_state()

    def _track_signal_results(self):
        """Check old signals: did they hit target or SL? Auto-train accuracy."""
        active = self.indices[self.active_index]
        chain = active.chain
        if not chain:
            return

        for sig in self.signal_history:
            if sig.get("result"):
                continue  # already tracked
            primary = sig.get("primary")
            if not primary:
                continue

            # Parse strike and side
            strike_str = primary.get("strike", "")
            parts = strike_str.split()
            if len(parts) < 2:
                continue
            try:
                strike_num = float(parts[0])
            except ValueError:
                continue
            side = parts[1]  # CE or PE

            # Get current LTP for this strike
            strike_data = chain.get(strike_num, {})
            side_data = strike_data.get(side, {})
            current_ltp = side_data.get("last_price", 0)
            if current_ltp <= 0:
                continue

            # Get entry price
            cmp_raw = primary.get("cmp_raw", 0)
            if not cmp_raw:
                continue

            # Check time elapsed (only track after 5+ minutes)
            sig_ts = sig.get("_ts", 0)
            if time.time() - sig_ts < 300:
                continue

            # Calculate current P&L %
            pnl_pct = ((current_ltp - cmp_raw) / cmp_raw) * 100

            # Check if target or SL hit
            if pnl_pct >= 35:  # ~target1 hit
                sig["result"] = "TARGET_HIT"
                sig["result_pnl"] = round(pnl_pct, 1)
                sig["result_ltp"] = current_ltp
            elif pnl_pct <= -25:  # SL hit
                sig["result"] = "SL_HIT"
                sig["result_pnl"] = round(pnl_pct, 1)
                sig["result_ltp"] = current_ltp
            elif time.time() - sig_ts > 1800:  # 30 min timeout
                if pnl_pct > 0:
                    sig["result"] = "TIME_EXIT_PROFIT"
                else:
                    sig["result"] = "TIME_EXIT_LOSS"
                sig["result_pnl"] = round(pnl_pct, 1)
                sig["result_ltp"] = current_ltp

            # Update current LTP for live tracking
            sig["current_ltp"] = current_ltp
            sig["current_pnl_pct"] = round(pnl_pct, 1)

    def _get_accuracy_stats(self) -> dict:
        """Calculate overall accuracy from tracked signals."""
        tracked = [s for s in self.signal_history if s.get("result")]
        if not tracked:
            return {"total": 0, "wins": 0, "losses": 0, "accuracy": 0, "avg_pnl": 0}
        wins = sum(1 for s in tracked if s["result"] in ("TARGET_HIT", "TIME_EXIT_PROFIT"))
        losses = sum(1 for s in tracked if s["result"] in ("SL_HIT", "TIME_EXIT_LOSS"))
        total_pnl = sum(s.get("result_pnl", 0) for s in tracked)
        return {
            "total": len(tracked),
            "wins": wins,
            "losses": losses,
            "accuracy": round((wins / len(tracked)) * 100, 1) if tracked else 0,
            "avg_pnl": round(total_pnl / len(tracked), 1) if tracked else 0,
            "best_trade": max((s.get("result_pnl", 0) for s in tracked), default=0),
            "worst_trade": min((s.get("result_pnl", 0) for s in tracked), default=0),
        }

    def _analyze_zones(self) -> dict:
        """Analyze chain OI data to find trading zones — reversal, buying, selling, trap."""
        active = self.indices[self.active_index]
        chain = active.chain
        spot = active.spot
        if not chain or spot <= 0:
            return {}

        strikes = sorted(chain.keys())
        # Collect OI data per strike
        pe_selling = []  # high PE OI = support (writers believe market won't fall)
        ce_selling = []  # high CE OI = resistance (writers believe market won't rise)
        pe_buying = []   # high PE OI change + price up = fear buying
        ce_buying = []   # high CE OI change + price up = bullish buying

        for s in strikes:
            ce = chain[s].get("CE") or {}
            pe = chain[s].get("PE") or {}
            ce_oi = ce.get("oi", 0)
            pe_oi = pe.get("oi", 0)
            ce_oi_chg = ce.get("oi_day_change", 0)
            pe_oi_chg = pe.get("oi_day_change", 0)
            ce_nc = ce.get("net_change", 0)
            pe_nc = pe.get("net_change", 0)

            # PE selling = OI building + price falling → support zone
            if pe_oi_chg > 0 and pe_nc <= 0 and pe_oi > 0:
                pe_selling.append({"strike": s, "oi": pe_oi, "oi_chg": pe_oi_chg, "price": pe.get("last_price", 0)})
            # CE selling = OI building + price falling → resistance zone
            if ce_oi_chg > 0 and ce_nc <= 0 and ce_oi > 0:
                ce_selling.append({"strike": s, "oi": ce_oi, "oi_chg": ce_oi_chg, "price": ce.get("last_price", 0)})
            # PE buying = OI building + price rising → bearish fear
            if pe_oi_chg > 0 and pe_nc > 0:
                pe_buying.append({"strike": s, "oi": pe_oi, "oi_chg": pe_oi_chg, "price": pe.get("last_price", 0)})
            # CE buying = OI building + price rising → bullish conviction
            if ce_oi_chg > 0 and ce_nc > 0:
                ce_buying.append({"strike": s, "oi": ce_oi, "oi_chg": ce_oi_chg, "price": ce.get("last_price", 0)})

        # Sort by OI (highest first)
        pe_selling.sort(key=lambda x: x["oi"], reverse=True)
        ce_selling.sort(key=lambda x: x["oi"], reverse=True)
        pe_buying.sort(key=lambda x: x["oi_chg"], reverse=True)
        ce_buying.sort(key=lambda x: x["oi_chg"], reverse=True)

        # Identify zones
        support_zone = pe_selling[0]["strike"] if pe_selling else 0
        resistance_zone = ce_selling[0]["strike"] if ce_selling else 0

        # Trap detection: if OI is building heavily at a strike near spot but price isn't moving
        trap_zones = []
        for s in strikes:
            ce = chain[s].get("CE") or {}
            pe = chain[s].get("PE") or {}
            ce_oi_chg = ce.get("oi_day_change", 0)
            pe_oi_chg = pe.get("oi_day_change", 0)
            # Both sides building OI near ATM = potential trap
            if abs(s - spot) <= active.cfg["strike_step"] * 3:
                if ce_oi_chg > 0 and pe_oi_chg > 0:
                    trap_zones.append({"strike": s, "ce_oi_chg": ce_oi_chg, "pe_oi_chg": pe_oi_chg})

        # Buyers vs Sellers winner
        total_ce_oi_chg = sum(ce.get("oi_day_change", 0) for s in strikes for ce in [chain[s].get("CE") or {}])
        total_pe_oi_chg = sum(pe.get("oi_day_change", 0) for s in strikes for pe in [chain[s].get("PE") or {}])
        total_ce_selling = sum(x["oi_chg"] for x in ce_selling)
        total_pe_selling = sum(x["oi_chg"] for x in pe_selling)
        total_ce_buying = sum(x["oi_chg"] for x in ce_buying)
        total_pe_buying = sum(x["oi_chg"] for x in pe_buying)

        # Reversal zone: where max pain is + where OI is highest on both sides
        reversal_strike = 0
        max_combined = 0
        for s in strikes:
            ce = chain[s].get("CE") or {}
            pe = chain[s].get("PE") or {}
            combined = ce.get("oi", 0) + pe.get("oi", 0)
            if combined > max_combined:
                max_combined = combined
                reversal_strike = s

        buyers_winning = total_pe_selling > total_ce_selling  # more PE selling = bullish = buyers winning
        winner = "BUYERS" if buyers_winning else "SELLERS"

        return {
            "support_zone": support_zone,
            "resistance_zone": resistance_zone,
            "reversal_zone": reversal_strike,
            "range": f"{int(support_zone)}–{int(resistance_zone)}" if support_zone and resistance_zone else "",
            "trap_zones": trap_zones[:3],
            "pe_selling": pe_selling[:5],
            "ce_selling": ce_selling[:5],
            "pe_buying": pe_buying[:5],
            "ce_buying": ce_buying[:5],
            "winner": winner,
            "buyers_score": total_pe_selling + total_ce_buying,
            "sellers_score": total_ce_selling + total_pe_buying,
            "total_ce_oi_chg": total_ce_oi_chg,
            "total_pe_oi_chg": total_pe_oi_chg,
        }

    def get_state(self) -> dict:
        active_state = self.indices[self.active_index]
        return {
            "active_index": self.active_index,
            "indices": {k: v.to_dict() for k, v in self.indices.items()},
            "spots": {k: v.spot for k, v in self.indices.items()},
            "alert_log": self.alert_log[-30:],
            "flow_tape": self.flow_tape[-50:],
            "timestamp": now_ist_iso(),
            # Active index shortcut fields
            "spot": active_state.spot,
            "atm": active_state.atm,
            "detectors": active_state.detectors,
            "confluence": active_state.confluence,
            "brain": active_state.brain,
            "strike_map": active_state.strike_map,
            "chain_summary": active_state._chain_summary(),
            "error": active_state.error,
            # v3 fields
            "ai_analysis": self.ai_analysis,
            "signal_history": self.signal_history[-10:],
            "last_signal": self.last_signal,
            "fii_dii": self.fii_dii,
            "ticker_active": self.ticker is not None and self.ticker._running if self.ticker else False,
            # VIX
            "india_vix": self.india_vix,
            "vix_enabled": self.vix_enabled,
            # Trend & Gap data
            "trend_data": self.trend_data,
            "timeframe_data": self.tf_engine.get_cached(self.active_index),
            "mtf_analysis": self.mtf_analysis,
            # Zone analysis
            "zone_analysis": self._analyze_zones(),
            # Check Trades — MTF + OI setups
            "check_trades": self.check_trades,
            # Accuracy tracking (auto-train)
            "accuracy": self._get_accuracy_stats(),
            # OTM trades from brain signal
            "otm_trades": active_state.brain.get("otm_trades", []),
            # Bob the Buyer
            "bob_signal": active_state.bob_signal,
            # Expiry info
            "selected_expiry": self.selected_expiry,
        }


user_aggregators: dict[str, UserAggregator] = {}

def get_or_create_aggregator(session_id: str, kite: KiteClient, ticker: KiteTicker | None = None) -> UserAggregator:
    if session_id not in user_aggregators:
        user_aggregators[session_id] = UserAggregator(kite, ticker)
    else:
        user_aggregators[session_id].kite = kite
        if ticker and not user_aggregators[session_id].ticker:
            user_aggregators[session_id].ticker = ticker
    return user_aggregators[session_id]

def remove_aggregator(session_id: str):
    user_aggregators.pop(session_id, None)
