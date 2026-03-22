"""Kite WebSocket Ticker — Real tick-by-tick data via Zerodha's binary WebSocket protocol.

Connects to wss://ws.kite.trade, subscribes to option instrument tokens in "full" mode,
parses binary ticks, and accumulates:
  - trade_log: detected large trades (block prints)
  - sweep_events: detected strike ladder sweeps
  - flow_data: real buy_pct per instrument from total_buy_qty / total_sell_qty
  - tick_store: latest tick data per token
"""

import asyncio
import json
import struct
import time
from collections import defaultdict
from datetime import datetime

import websockets


WS_URL = "wss://ws.kite.trade/"


class KiteTicker:
    """Async Kite WebSocket ticker with binary parsing and trade detection."""

    def __init__(self, api_key: str, access_token: str):
        self.api_key = api_key
        self.access_token = access_token
        self.ws = None
        self._task: asyncio.Task | None = None
        self._running = False

        # Token → instrument info mapping (set externally)
        self.token_map: dict[int, dict] = {}  # token → {strike, side, tradingsymbol, lot_size, index}

        # Live state
        self.tick_store: dict[int, dict] = {}       # token → latest tick
        self.trade_log: list[dict] = []              # detected large trades
        self.sweep_events: list[dict] = []           # detected sweeps
        self.flow_data: dict[int, dict] = {}         # token → {buy_qty, sell_qty, buy_pct, volume}

        # Internal tracking
        self._prev_volumes: dict[int, int] = {}      # token → previous volume (for delta)
        self._prev_last_qty: dict[int, int] = {}     # token → previous last_quantity
        self._volume_bursts: list[dict] = []          # recent volume bursts for sweep detection
        self._last_sweep_check: float = 0

    async def connect(self):
        """Connect to Kite WebSocket."""
        url = f"{WS_URL}?api_key={self.api_key}&access_token={self.access_token}"
        try:
            self.ws = await websockets.connect(
                url,
                ping_interval=10,
                ping_timeout=5,
                close_timeout=3,
                max_size=2**20,
            )
            self._running = True
            print(f"[TICKER] Connected to Kite WebSocket")
            return True
        except Exception as e:
            print(f"[TICKER] Connection failed: {e}")
            return False

    async def subscribe(self, tokens: list[int]):
        """Subscribe to instrument tokens in full mode."""
        if not self.ws or not tokens:
            return
        try:
            await self.ws.send(json.dumps({"a": "subscribe", "v": tokens}))
            await self.ws.send(json.dumps({"a": "mode", "v": ["full", tokens]}))
            print(f"[TICKER] Subscribed to {len(tokens)} tokens in full mode")
        except Exception as e:
            print(f"[TICKER] Subscribe failed: {e}")

    async def start(self):
        """Start the ticker listener in background."""
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._listen_loop())

    async def stop(self):
        """Stop the ticker."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
        print("[TICKER] Stopped")

    async def _listen_loop(self):
        """Main listen loop with auto-reconnect."""
        while self._running:
            try:
                if not self.ws or self.ws.closed:
                    ok = await self.connect()
                    if not ok:
                        await asyncio.sleep(5)
                        continue
                    # Re-subscribe to known tokens
                    if self.token_map:
                        await self.subscribe(list(self.token_map.keys()))

                async for msg in self.ws:
                    if not self._running:
                        break
                    if isinstance(msg, bytes):
                        if len(msg) <= 1:
                            continue  # heartbeat
                        self._process_binary(msg)
                    # Text messages (order updates etc) — ignore

            except websockets.ConnectionClosed:
                print("[TICKER] Connection closed, reconnecting in 3s...")
                await asyncio.sleep(3)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[TICKER] Error: {e}, reconnecting in 5s...")
                await asyncio.sleep(5)

    # ── Binary parsing ──

    def _process_binary(self, data: bytes):
        """Parse Kite binary message into ticks and process them."""
        try:
            packets = self._split_packets(data)
            for pkt in packets:
                tick = self._parse_packet(pkt)
                if tick:
                    self._on_tick(tick)
        except Exception as e:
            pass  # silently skip malformed packets

    @staticmethod
    def _split_packets(data: bytes) -> list[bytes]:
        """Split binary message into individual instrument packets."""
        if len(data) < 2:
            return []
        num = struct.unpack(">H", data[0:2])[0]
        packets = []
        offset = 2
        for _ in range(num):
            if offset + 2 > len(data):
                break
            pkt_len = struct.unpack(">H", data[offset:offset + 2])[0]
            if offset + 2 + pkt_len > len(data):
                break
            packets.append(data[offset + 2:offset + 2 + pkt_len])
            offset += 2 + pkt_len
        return packets

    @staticmethod
    def _unpack(data: bytes, start: int, end: int, signed: bool = False) -> int:
        fmt = ">i" if signed else ">I"
        return struct.unpack(fmt, data[start:end])[0]

    def _parse_packet(self, pkt: bytes) -> dict | None:
        """Parse a single instrument packet. Full mode = 184 bytes for F&O."""
        n = len(pkt)
        if n < 4:
            return None

        token = self._unpack(pkt, 0, 4)
        divisor = 100.0

        if n == 8:
            # LTP mode
            return {
                "token": token,
                "last_price": self._unpack(pkt, 4, 8) / divisor,
                "mode": "ltp",
            }

        if n in (28, 32):
            # Index quote/full
            d = {
                "token": token,
                "last_price": self._unpack(pkt, 4, 8) / divisor,
                "high": self._unpack(pkt, 8, 12) / divisor,
                "low": self._unpack(pkt, 12, 16) / divisor,
                "open": self._unpack(pkt, 16, 20) / divisor,
                "close": self._unpack(pkt, 20, 24) / divisor,
                "change": self._unpack(pkt, 24, 28, signed=True) / divisor,
                "mode": "index_quote" if n == 28 else "index_full",
            }
            return d

        if n == 44 or n == 184:
            # Non-index quote or full (F&O derivatives)
            d = {
                "token": token,
                "last_price": self._unpack(pkt, 4, 8) / divisor,
                "last_quantity": self._unpack(pkt, 8, 12),
                "average_price": self._unpack(pkt, 12, 16) / divisor,
                "volume": self._unpack(pkt, 16, 20),
                "buy_quantity": self._unpack(pkt, 20, 24),
                "sell_quantity": self._unpack(pkt, 24, 28),
                "open": self._unpack(pkt, 28, 32) / divisor,
                "high": self._unpack(pkt, 32, 36) / divisor,
                "low": self._unpack(pkt, 36, 40) / divisor,
                "close": self._unpack(pkt, 40, 44) / divisor,
                "mode": "quote" if n == 44 else "full",
            }

            if n == 184:
                d["last_trade_time"] = self._unpack(pkt, 44, 48)
                d["oi"] = self._unpack(pkt, 48, 52)
                d["oi_day_high"] = self._unpack(pkt, 52, 56)
                d["oi_day_low"] = self._unpack(pkt, 56, 60)
                d["exchange_timestamp"] = self._unpack(pkt, 60, 64)

                # Market depth: 5 buy + 5 sell, 12 bytes each
                depth_buy, depth_sell = [], []
                offset = 64
                for i in range(10):
                    entry = {
                        "quantity": self._unpack(pkt, offset, offset + 4),
                        "price": self._unpack(pkt, offset + 4, offset + 8) / divisor,
                        "orders": struct.unpack(">H", pkt[offset + 8:offset + 10])[0],
                    }
                    offset += 12
                    if i < 5:
                        depth_buy.append(entry)
                    else:
                        depth_sell.append(entry)
                d["depth"] = {"buy": depth_buy, "sell": depth_sell}

            return d

        return None

    # ── Tick processing & trade detection ──

    def _on_tick(self, tick: dict):
        """Process a tick: update stores, detect trades, sweeps, flow."""
        token = tick["token"]
        self.tick_store[token] = tick
        info = self.token_map.get(token)
        if not info:
            return

        # Order flow data
        buy_qty = tick.get("buy_quantity", 0)
        sell_qty = tick.get("sell_quantity", 0)
        total = buy_qty + sell_qty
        self.flow_data[token] = {
            "buy_qty": buy_qty,
            "sell_qty": sell_qty,
            "buy_pct": buy_qty / total if total > 0 else 0.5,
            "volume": tick.get("volume", 0),
            "oi": tick.get("oi", 0),
            "last_price": tick.get("last_price", 0),
        }

        # Volume delta — detect new trades
        vol = tick.get("volume", 0)
        prev_vol = self._prev_volumes.get(token, 0)
        vol_delta = vol - prev_vol if prev_vol > 0 else 0
        self._prev_volumes[token] = vol

        if vol_delta <= 0:
            return

        lot_size = info.get("lot_size", 25)
        lots_traded = vol_delta // lot_size if lot_size > 0 else vol_delta
        last_qty = tick.get("last_quantity", 0)
        last_lots = last_qty // lot_size if lot_size > 0 else last_qty
        now = datetime.now()

        # Block print detection: last trade >= 500 lots
        if last_lots >= 500:
            is_buy = buy_qty > sell_qty
            self.trade_log.append({
                "time": now.isoformat(),
                "strike": info["strike"],
                "side": info["side"],
                "size": last_lots,
                "is_buy": is_buy,
                "price": tick.get("last_price", 0),
                "token": token,
            })

        # Repeat buyer detection: any trade >= 50 lots goes to trade_log
        elif last_lots >= 50:
            is_buy = buy_qty > sell_qty
            self.trade_log.append({
                "time": now.isoformat(),
                "strike": info["strike"],
                "side": info["side"],
                "size": last_lots,
                "is_buy": is_buy,
                "price": tick.get("last_price", 0),
                "token": token,
            })

        # Track volume bursts for sweep detection
        if lots_traded >= 100:
            self._volume_bursts.append({
                "time": time.time(),
                "strike": info["strike"],
                "side": info["side"],
                "lots": lots_traded,
                "token": token,
            })
            self._detect_sweeps()

        # Trim logs
        self.trade_log = self.trade_log[-500:]
        self._volume_bursts = [b for b in self._volume_bursts if time.time() - b["time"] < 120]

    def _detect_sweeps(self):
        """Detect strike ladder sweeps: 3+ consecutive strikes bought within 60s."""
        now = time.time()
        if now - self._last_sweep_check < 5:
            return
        self._last_sweep_check = now

        recent = [b for b in self._volume_bursts if now - b["time"] < 60]
        if len(recent) < 3:
            return

        # Group by side
        by_side: dict[str, list] = defaultdict(list)
        for b in recent:
            by_side[b["side"]].append(b)

        for side, bursts in by_side.items():
            strikes = sorted(set(b["strike"] for b in bursts))
            if len(strikes) < 3:
                continue

            # Find consecutive strike sequences
            consecutive = []
            current_run = [strikes[0]]
            for i in range(1, len(strikes)):
                diff = strikes[i] - strikes[i - 1]
                if diff <= 100:  # Within one strike step
                    current_run.append(strikes[i])
                else:
                    if len(current_run) >= 3:
                        consecutive.append(current_run[:])
                    current_run = [strikes[i]]
            if len(current_run) >= 3:
                consecutive.append(current_run)

            for run in consecutive:
                total_lots = sum(b["lots"] for b in bursts if b["strike"] in run)
                times = [b["time"] for b in bursts if b["strike"] in run]
                self.sweep_events.append({
                    "side": side,
                    "strikes": run,
                    "total_lots": total_lots,
                    "start_time": datetime.fromtimestamp(min(times)).isoformat(),
                    "end_time": datetime.fromtimestamp(max(times)).isoformat(),
                    "detected_at": datetime.now().isoformat(),
                })

        # Keep only last 50 sweeps
        self.sweep_events = self.sweep_events[-50:]

    # ── Data accessors for data_aggregator ──

    def get_flow_for_chain(self, chain: dict, index_name: str) -> dict:
        """Return buy_pct mapping for chain strikes using real tick data.
        Returns: {strike: {CE: {buy_pct, volume, oi}, PE: {...}}}
        """
        result = {}
        for token, flow in self.flow_data.items():
            info = self.token_map.get(token)
            if not info or info.get("index") != index_name:
                continue
            strike = info["strike"]
            side = info["side"]
            if strike not in result:
                result[strike] = {}
            result[strike][side] = flow
        return result

    def get_trade_log(self, index_name: str | None = None) -> list[dict]:
        """Get accumulated trade log, optionally filtered by index."""
        if not index_name:
            return self.trade_log[-200:]
        return [t for t in self.trade_log if self.token_map.get(t.get("token"), {}).get("index") == index_name][-200:]

    def get_sweep_events(self, index_name: str | None = None) -> list[dict]:
        """Get detected sweep events."""
        if not index_name:
            return self.sweep_events[-20:]
        result = []
        for ev in self.sweep_events:
            # Check if any strike in this sweep belongs to the index
            if ev.get("side"):
                # All sweeps are returned since we don't track index per sweep currently
                result.append(ev)
        return result[-20:]

    def clear_consumed(self):
        """Clear consumed data after a run_cycle to avoid double-counting."""
        self.trade_log.clear()
        self.sweep_events.clear()
        self._volume_bursts.clear()

    def register_tokens(self, chain: dict, index_name: str, lot_size: int):
        """Register instrument tokens from option chain for subscription.
        chain: {strike: {CE: {instrument_token, tradingsymbol, ...}, PE: {...}}}
        """
        new_tokens = []
        for strike, sides in chain.items():
            for side_key in ("CE", "PE"):
                info = sides.get(side_key)
                if not info or not info.get("instrument_token"):
                    continue
                token = int(info["instrument_token"])
                if token not in self.token_map:
                    self.token_map[token] = {
                        "strike": float(strike),
                        "side": side_key,
                        "tradingsymbol": info.get("tradingsymbol", ""),
                        "lot_size": lot_size,
                        "index": index_name,
                    }
                    new_tokens.append(token)
        return new_tokens
