"""VPIN Engine — Volume-Synchronized Probability of Informed Trading.

Measures flow toxicity in real-time from Kite WebSocket ticks.
Source: Nifty Futures (leading indicator) → Trade vehicle: Options CE/PE buy.

Core logic:
1. Accumulate ticks into fixed-volume buckets
2. Classify each trade as buy/sell using BVC (Bulk Volume Classification)
3. VPIN = rolling average of order imbalance over last N buckets
4. Signal levels: NEUTRAL < 0.55 < ELEVATED < 0.70 < HIGH < 0.85 < EXTREME
"""

import math
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

IST = timezone(timedelta(hours=5, minutes=30))

# ── Inline normal CDF (no scipy dependency) ──
def _norm_cdf(x: float) -> float:
    """Standard normal CDF using Abramowitz & Stegun approximation. Max error ~1.5e-7."""
    if x < -6:
        return 0.0
    if x > 6:
        return 1.0
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p = 0.3275911
    sign = 1 if x >= 0 else -1
    x = abs(x)
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x / 2)
    return 0.5 * (1.0 + sign * y)


# ── Signal thresholds ──
SIGNAL_NEUTRAL = 0.55
SIGNAL_ELEVATED = 0.70
SIGNAL_HIGH = 0.85

def classify_signal(vpin: float) -> tuple[str, str]:
    """Returns (signal_name, advice)."""
    if vpin >= SIGNAL_HIGH:
        return "EXTREME", "Avoid longs, hedge immediately. Institutional flow detected."
    elif vpin >= SIGNAL_ELEVATED:
        return "HIGH", "Reduce position size, trail SL tight. Informed activity building."
    elif vpin >= SIGNAL_NEUTRAL:
        return "ELEVATED", "Watch closely. Informed activity starting to build."
    else:
        return "NEUTRAL", "Normal conditions. Safe to trade with standard risk."


@dataclass
class Bucket:
    """One volume bucket."""
    start_time: str = ""
    end_time: str = ""
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    total_volume: float = 0.0
    vwap: float = 0.0
    trades: int = 0
    imbalance: float = 0.0  # |buy - sell| / total
    oi: int = 0

    def to_dict(self) -> dict:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "buy_volume": round(self.buy_volume),
            "sell_volume": round(self.sell_volume),
            "total_volume": round(self.total_volume),
            "vwap": round(self.vwap, 2),
            "trades": self.trades,
            "imbalance": round(self.imbalance, 4),
            "oi": self.oi,
        }


class InstrumentVPIN:
    """VPIN calculator for a single instrument (futures or option)."""

    def __init__(self, token: int, name: str, bucket_volume: int = 30000, window: int = 50):
        self.token = token
        self.name = name
        self.bucket_volume = bucket_volume
        self.window = window

        # Current accumulating bucket
        self._current_buy: float = 0.0
        self._current_sell: float = 0.0
        self._current_vol: float = 0.0
        self._current_value: float = 0.0  # for VWAP
        self._current_trades: int = 0
        self._current_start: str = ""
        self._current_oi: int = 0

        # Previous tick for sigma estimation
        self._prev_price: float = 0.0
        self._returns: deque = deque(maxlen=200)
        self._sigma: float = 0.01  # initial volatility estimate

        # Completed buckets
        self.buckets: deque[Bucket] = deque(maxlen=500)

        # Rolling VPIN
        self.vpin: float = 0.0
        self.signal: str = "NEUTRAL"
        self.advice: str = "Normal conditions."
        self.last_update: float = 0.0

        # Stats
        self.total_ticks: int = 0
        self.total_volume: int = 0

    def process_tick(self, price: float, volume: int, oi: int = 0) -> Optional[dict]:
        """Process a single tick. Returns bucket dict if a bucket was completed."""
        if price <= 0 or volume <= 0:
            return None

        now = datetime.now(IST)
        ts = now.strftime("%H:%M:%S")

        self.total_ticks += 1
        self.total_volume += volume

        if not self._current_start:
            self._current_start = ts

        self._current_oi = oi if oi > 0 else self._current_oi

        # ── Update volatility estimate ──
        if self._prev_price > 0:
            ret = math.log(price / self._prev_price)
            self._returns.append(ret)
            if len(self._returns) >= 20:
                mean = sum(self._returns) / len(self._returns)
                variance = sum((r - mean) ** 2 for r in self._returns) / len(self._returns)
                self._sigma = max(0.0001, math.sqrt(variance))
        self._prev_price = price

        # ── BVC: Bulk Volume Classification ──
        # Split volume into buy/sell using normal CDF of standardized price change
        if self._sigma > 0 and self._prev_price > 0 and len(self._returns) > 0:
            z = self._returns[-1] / self._sigma if self._sigma > 0 else 0
            buy_prob = _norm_cdf(z)
        else:
            buy_prob = 0.5  # no info yet

        buy_vol = volume * buy_prob
        sell_vol = volume * (1 - buy_prob)

        self._current_buy += buy_vol
        self._current_sell += sell_vol
        self._current_vol += volume
        self._current_value += price * volume
        self._current_trades += 1

        # ── Check if bucket is full ──
        completed = None
        if self._current_vol >= self.bucket_volume:
            vwap = self._current_value / self._current_vol if self._current_vol > 0 else price
            total = self._current_buy + self._current_sell
            imbalance = abs(self._current_buy - self._current_sell) / total if total > 0 else 0

            bucket = Bucket(
                start_time=self._current_start,
                end_time=ts,
                buy_volume=self._current_buy,
                sell_volume=self._current_sell,
                total_volume=self._current_vol,
                vwap=vwap,
                trades=self._current_trades,
                imbalance=imbalance,
                oi=self._current_oi,
            )
            self.buckets.append(bucket)
            completed = bucket.to_dict()

            # Reset for next bucket
            self._current_buy = 0.0
            self._current_sell = 0.0
            self._current_vol = 0.0
            self._current_value = 0.0
            self._current_trades = 0
            self._current_start = ""

            # ── Recalculate VPIN ──
            self._update_vpin()

        self.last_update = time.time()
        return completed

    def _update_vpin(self):
        """VPIN = average imbalance of last N buckets."""
        recent = list(self.buckets)[-self.window:]
        if not recent:
            self.vpin = 0.0
        else:
            self.vpin = sum(b.imbalance for b in recent) / len(recent)
        self.signal, self.advice = classify_signal(self.vpin)

    def get_state(self) -> dict:
        """Current state for API response."""
        recent = list(self.buckets)[-self.window:]
        sparkline = [round(b.imbalance, 4) for b in recent]

        total_buy = sum(b.buy_volume for b in recent) if recent else 0
        total_sell = sum(b.sell_volume for b in recent) if recent else 0

        # Current bucket progress
        bucket_progress = self._current_vol / self.bucket_volume if self.bucket_volume > 0 else 0

        return {
            "token": self.token,
            "name": self.name,
            "vpin": round(self.vpin, 4),
            "signal": self.signal,
            "advice": self.advice,
            "buy_volume": round(total_buy),
            "sell_volume": round(total_sell),
            "buckets_completed": len(self.buckets),
            "bucket_progress": round(bucket_progress, 2),
            "sparkline": sparkline,
            "total_ticks": self.total_ticks,
            "total_volume": self.total_volume,
            "last_update": self.last_update,
            "sigma": round(self._sigma, 6),
        }

    def get_history(self, n: int = 50) -> list[dict]:
        """Last N buckets as dicts."""
        return [b.to_dict() for b in list(self.buckets)[-n:]]


class VPINEngine:
    """Manages VPIN: 1 Futures + 2 merged sides (CE Side, PE Side).

    Architecture:
    - NIFTY-FUT: standalone, bucket=30K (leading indicator)
    - CE SIDE: ALL CE option ticks merged into one VPIN (bucket=10K)
    - PE SIDE: ALL PE option ticks merged into one VPIN (bucket=10K)
    - Individual option tokens are mapped to their side for routing.
    """

    # Virtual token IDs for merged sides
    CE_SIDE_TOKEN = -1
    PE_SIDE_TOKEN = -2

    def __init__(self):
        self.instruments: dict[int, InstrumentVPIN] = {}
        # Map real option tokens → side for routing
        self._option_side_map: dict[int, str] = {}  # token → "CE" or "PE"

    def register_futures(self, token: int, name: str = "NIFTY-FUT"):
        """Register futures instrument for standalone VPIN."""
        if token not in self.instruments:
            self.instruments[token] = InstrumentVPIN(token, name, bucket_volume=30000, window=50)
            print(f"[VPIN] Registered {name} (token={token}, bucket=30000)")

    def register_sides(self):
        """Register merged CE Side and PE Side virtual instruments."""
        if self.CE_SIDE_TOKEN not in self.instruments:
            self.instruments[self.CE_SIDE_TOKEN] = InstrumentVPIN(self.CE_SIDE_TOKEN, "NIFTY CE SIDE", bucket_volume=10000, window=50)
            print(f"[VPIN] Registered CE SIDE (merged all CE strikes, bucket=10000)")
        if self.PE_SIDE_TOKEN not in self.instruments:
            self.instruments[self.PE_SIDE_TOKEN] = InstrumentVPIN(self.PE_SIDE_TOKEN, "NIFTY PE SIDE", bucket_volume=10000, window=50)
            print(f"[VPIN] Registered PE SIDE (merged all PE strikes, bucket=10000)")

    def register_option_token(self, token: int, side: str):
        """Map an option token to CE or PE side for tick routing."""
        if side in ("CE", "PE"):
            self._option_side_map[token] = side

    def process_tick(self, token: int, price: float, volume: int, oi: int = 0) -> Optional[dict]:
        """Process a tick. Routes to futures directly, options to merged side."""
        if price <= 0 or volume <= 0:
            return None

        # Direct instrument (futures)
        if token in self.instruments:
            return self.instruments[token].process_tick(price, volume, oi)

        # Option token → route to merged CE/PE side
        side = self._option_side_map.get(token)
        if side == "CE" and self.CE_SIDE_TOKEN in self.instruments:
            return self.instruments[self.CE_SIDE_TOKEN].process_tick(price, volume, oi)
        elif side == "PE" and self.PE_SIDE_TOKEN in self.instruments:
            return self.instruments[self.PE_SIDE_TOKEN].process_tick(price, volume, oi)

        return None

    def get_all_states(self) -> dict:
        """Get VPIN state for all 3 instruments: FUT, CE Side, PE Side."""
        states = {}
        for token, inst in self.instruments.items():
            states[str(token)] = inst.get_state()

        # Market toxicity = futures VPIN (primary leading indicator)
        futures_vpins = [inst.vpin for inst in self.instruments.values()
                         if "FUT" in inst.name.upper()]
        max_vpin = max(futures_vpins) if futures_vpins else 0
        signal, advice = classify_signal(max_vpin)

        # CE vs PE side comparison
        ce_inst = self.instruments.get(self.CE_SIDE_TOKEN)
        pe_inst = self.instruments.get(self.PE_SIDE_TOKEN)
        ce_vpin = ce_inst.vpin if ce_inst else 0
        pe_vpin = pe_inst.vpin if pe_inst else 0

        if ce_vpin > pe_vpin + 0.1:
            flow_bias = "CE SIDE ACTIVE — call buyers dominating"
        elif pe_vpin > ce_vpin + 0.1:
            flow_bias = "PE SIDE ACTIVE — put buyers dominating"
        else:
            flow_bias = "BALANCED — no clear side dominance"

        return {
            "instruments": states,
            "market_vpin": round(max_vpin, 4),
            "market_signal": signal,
            "market_advice": advice,
            "ce_vpin": round(ce_vpin, 4),
            "pe_vpin": round(pe_vpin, 4),
            "flow_bias": flow_bias,
            "option_tokens_mapped": len(self._option_side_map),
            "timestamp": datetime.now(IST).isoformat(),
        }

    def get_history(self, token: int, n: int = 50) -> list[dict]:
        """Get bucket history for an instrument."""
        inst = self.instruments.get(token)
        if not inst:
            return []
        return inst.get_history(n)


# ── Singleton ──
vpin_engine = VPINEngine()
