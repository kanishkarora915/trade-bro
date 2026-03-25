"""Zerodha Kite Connect API wrapper — per-user sessions with global caching + IV calculation."""
import hashlib
import math
import time
import httpx
from datetime import datetime, timedelta
from config import NIFTY_STRIKE_STEP, OPTION_CHAIN_RANGE


# --- Black-Scholes IV Solver ---
def _norm_cdf(x: float) -> float:
    """Standard normal CDF approximation (Abramowitz & Stegun)."""
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p = 0.3275911
    sign = 1 if x >= 0 else -1
    x = abs(x)
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x / 2.0)
    return 0.5 * (1.0 + sign * y)


def _bs_price(S: float, K: float, T: float, r: float, sigma: float, is_call: bool) -> float:
    """Black-Scholes option price."""
    if sigma <= 0 or T <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + sigma * sigma / 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if is_call:
        return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    else:
        return K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)


def _bs_vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Black-Scholes vega (sensitivity to volatility)."""
    if sigma <= 0 or T <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + sigma * sigma / 2) * T) / (sigma * math.sqrt(T))
    return S * math.sqrt(T) * math.exp(-d1 * d1 / 2) / math.sqrt(2 * math.pi)


def calculate_iv(option_price: float, spot: float, strike: float, T: float, is_call: bool,
                 r: float = 0.07, max_iter: int = 20) -> float:
    """Calculate implied volatility using Newton-Raphson. Returns IV as percentage (e.g., 18.5)."""
    if option_price <= 0 or spot <= 0 or strike <= 0 or T <= 0:
        return 0.0
    # Intrinsic value check
    intrinsic = max(0, spot - strike) if is_call else max(0, strike - spot)
    if option_price < intrinsic * 0.5:
        return 0.0

    sigma = 0.25  # initial guess 25%
    for _ in range(max_iter):
        price = _bs_price(spot, strike, T, r, sigma, is_call)
        vega = _bs_vega(spot, strike, T, r, sigma)
        if vega < 1e-8:
            break
        sigma = sigma - (price - option_price) / vega
        if sigma <= 0.01:
            sigma = 0.01
        if sigma > 5.0:
            return 0.0  # diverged
    return round(sigma * 100, 2)  # return as percentage

BASE = "https://api.kite.trade"
LOGIN_URL = "https://kite.zerodha.com/connect/login?v=3&api_key="

# Global instruments cache — shared across all users, refreshed every 4 hours
_instruments_cache: dict[str, tuple[float, list[dict]]] = {}  # exchange -> (timestamp, data)
_INSTRUMENTS_TTL = 4 * 3600  # 4 hours


class KiteClient:
    """Per-user Kite API client with aggressive caching."""

    def __init__(self, api_key: str, access_token: str):
        self.api_key = api_key
        self.access_token = access_token
        self.headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {api_key}:{access_token}",
        }

    @staticmethod
    def get_login_url(api_key: str) -> str:
        return f"{LOGIN_URL}{api_key}"

    @staticmethod
    async def generate_session(api_key: str, api_secret: str, request_token: str) -> dict:
        checksum = hashlib.sha256(
            f"{api_key}{request_token}{api_secret}".encode()
        ).hexdigest()

        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE}/session/token",
                data={
                    "api_key": api_key,
                    "request_token": request_token,
                    "checksum": checksum,
                },
            )
            if r.status_code != 200:
                return {"error": r.text}
            data = r.json().get("data", {})
            return {
                "access_token": data.get("access_token", ""),
                "user_id": data.get("user_id", ""),
                "user_name": data.get("user_name", ""),
            }

    async def _get(self, path: str, params: list | None = None) -> httpx.Response:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(f"{BASE}{path}", params=params, headers=self.headers)
            r.raise_for_status()
            return r

    async def get_instruments(self, exchange: str = "NFO") -> list[dict]:
        """Get instruments with global 4-hour cache (shared across users)."""
        now = time.time()
        if exchange in _instruments_cache:
            ts, data = _instruments_cache[exchange]
            if now - ts < _INSTRUMENTS_TTL:
                return data

        print(f"[KITE] Fetching instruments for {exchange}...")
        r = await self._get(f"/instruments/{exchange}")
        lines = r.text.strip().split("\n")
        header = [h.strip().strip('"') for h in lines[0].split(",")]
        rows = []
        for line in lines[1:]:
            vals = [v.strip().strip('"') for v in line.split(",")]
            if len(vals) == len(header):
                rows.append(dict(zip(header, vals)))
        _instruments_cache[exchange] = (now, rows)
        # Verify name field is clean (no stray quotes)
        sample_names = set(r.get("name", "") for r in rows[:100])
        print(f"[KITE] Cached {len(rows)} instruments for {exchange}, sample names: {list(sample_names)[:5]}")
        return rows

    async def get_options(self, name: str = "NIFTY", expiry: str | None = None) -> list[dict]:
        exchange = "BFO" if name == "SENSEX" else "NFO"
        segment = f"{exchange}-OPT"
        instruments = await self.get_instruments(exchange)
        opts = [
            i for i in instruments
            if i.get("name") == name
            and i.get("instrument_type") in ("CE", "PE")
            and i.get("segment") == segment
        ]
        if expiry:
            opts = [i for i in opts if i.get("expiry") == expiry]
        else:
            # CRITICAL: Filter out expired expiries (fixes weekend/holiday loading)
            today_str = datetime.now().strftime("%Y-%m-%d")
            all_expiries = sorted(set(i["expiry"] for i in opts))
            future_expiries = [e for e in all_expiries if e >= today_str]
            # If no future expiry found, use the most recent past one (for after-hours data)
            if future_expiries:
                nearest = future_expiries[0]
            elif all_expiries:
                nearest = all_expiries[-1]  # most recent past expiry
            else:
                return []
            opts = [i for i in opts if i["expiry"] == nearest]
            print(f"[KITE] {name} expiry selected: {nearest} (today={today_str}, total={len(all_expiries)}, future={len(future_expiries)})")
        return opts

    async def get_quote(self, instruments: list[str]) -> dict:
        params = [("i", i) for i in instruments[:500]]
        r = await self._get("/quote", params)
        return r.json().get("data", {})

    async def get_ltp(self, instruments: list[str]) -> dict:
        params = [("i", i) for i in instruments[:500]]
        r = await self._get("/quote/ltp", params)
        return r.json().get("data", {})

    async def get_historical(
        self, instrument_token: str, interval: str = "day",
        from_date: str | None = None, to_date: str | None = None,
    ) -> list[dict]:
        if not to_date:
            to_date = datetime.now().strftime("%Y-%m-%d")
        if not from_date:
            from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        r = await self._get(
            f"/instruments/historical/{instrument_token}/{interval}",
            [("from", from_date), ("to", to_date)],
        )
        candles = r.json().get("data", {}).get("candles", [])
        return [
            {"date": c[0], "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]}
            for c in candles
        ]

    async def build_option_chain(self, spot_price: float, expiry: str | None = None,
                                  name: str = "NIFTY", strike_step: int = 50, chain_range: int = 500) -> dict:
        opts = await self.get_options(name, expiry)
        if not opts:
            print(f"[KITE] WARNING: No options found for {name} — returning empty chain")
            atm = round(spot_price / strike_step) * strike_step
            return {"atm": atm, "expiry": "", "chain": {}, "timestamp": datetime.now().isoformat()}
        atm = round(spot_price / strike_step) * strike_step

        # Tighter range for faster fetching — ±10 strikes is enough for detectors
        tight_range = min(chain_range, strike_step * 10)
        low = atm - tight_range
        high = atm + tight_range

        exchange = "BFO" if name == "SENSEX" else "NFO"
        filtered = [o for o in opts if low <= float(o.get("strike", 0)) <= high]
        trading_symbols = [f"{exchange}:{o['tradingsymbol']}" for o in filtered]

        # Single batch — with tight range this is always < 500
        quotes = {}
        if trading_symbols:
            quotes = await self.get_quote(trading_symbols[:500])

        # Calculate time to expiry for IV calculation
        expiry_date_str = opts[0].get("expiry", "") if opts else ""
        T = 1 / 365  # default 1 day
        if expiry_date_str:
            try:
                exp_dt = datetime.strptime(expiry_date_str, "%Y-%m-%d").replace(hour=15, minute=30)
                now = datetime.now()
                diff = (exp_dt - now).total_seconds()
                T = max(diff / (365 * 24 * 3600), 0.0001)  # in years, min ~1 hour
            except ValueError:
                pass

        chain: dict[float, dict] = {}
        for o in filtered:
            strike = float(o["strike"])
            side = o["instrument_type"]
            key = f"{exchange}:{o['tradingsymbol']}"
            q = quotes.get(key, {})
            depth_buy = q.get("depth", {}).get("buy", [{}])
            depth_sell = q.get("depth", {}).get("sell", [{}])

            if strike not in chain:
                chain[strike] = {"strike": strike, "CE": None, "PE": None}

            total_buy_qty = q.get("buy_quantity", 0)
            total_sell_qty = q.get("sell_quantity", 0)
            total_qty = total_buy_qty + total_sell_qty
            real_buy_pct = total_buy_qty / total_qty if total_qty > 0 else 0.5

            vol = q.get("volume", 0)
            avg_price = q.get("average_price", 0)
            last_price = q.get("last_price", 0)
            avg_5d = max(1, vol // 3) if vol > 0 else 1

            bid_price = depth_buy[0].get("price", 0) if depth_buy else 0
            ask_price = depth_sell[0].get("price", 0) if depth_sell else 0
            spread_base = max(0.05, (ask_price - bid_price)) if bid_price > 0 and ask_price > 0 else 1.0

            # Calculate Implied Volatility using Black-Scholes
            is_call = (side == "CE")
            iv = calculate_iv(last_price, spot_price, strike, T, is_call)

            chain[strike][side] = {
                "tradingsymbol": o["tradingsymbol"],
                "instrument_token": o["instrument_token"],
                "last_price": last_price,
                "volume": vol,
                "oi": q.get("oi", 0),
                "oi_day_change": q.get("oi_day_change", 0),
                "bid": bid_price,
                "ask": ask_price,
                "bid_qty": depth_buy[0].get("quantity", 0) if depth_buy else 0,
                "ask_qty": depth_sell[0].get("quantity", 0) if depth_sell else 0,
                "buy_quantity": total_buy_qty,
                "sell_quantity": total_sell_qty,
                "iv": iv,
                "buy_pct": real_buy_pct,
                "avg_5d_volume": avg_5d,
                "spread_baseline": spread_base,
                "average_price": avg_price,
                "close": q.get("ohlc", {}).get("close", 0),
                "open": q.get("ohlc", {}).get("open", 0),
                "high": q.get("ohlc", {}).get("high", 0),
                "low": q.get("ohlc", {}).get("low", 0),
                "net_change": q.get("net_change", 0),
                "lower_circuit": q.get("lower_circuit_limit", 0),
                "upper_circuit": q.get("upper_circuit_limit", 0),
            }

        return {
            "atm": atm,
            "expiry": expiry_date_str,
            "chain": dict(sorted(chain.items())),
            "timestamp": datetime.now().isoformat(),
        }
