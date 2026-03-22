"""Zerodha Kite Connect API wrapper — per-user sessions."""
import hashlib
import httpx
from datetime import datetime, timedelta
from config import NIFTY_STRIKE_STEP, OPTION_CHAIN_RANGE

BASE = "https://api.kite.trade"
LOGIN_URL = "https://kite.zerodha.com/connect/login?v=3&api_key="


class KiteClient:
    """Per-user Kite API client."""

    def __init__(self, api_key: str, access_token: str):
        self.api_key = api_key
        self.access_token = access_token
        self.headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {api_key}:{access_token}",
        }
        self._instruments_cache: list[dict] | None = None

    @staticmethod
    def get_login_url(api_key: str) -> str:
        return f"{LOGIN_URL}{api_key}"

    @staticmethod
    async def generate_session(api_key: str, api_secret: str, request_token: str) -> dict:
        """Exchange request_token for access_token."""
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
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{BASE}{path}", params=params, headers=self.headers)
            r.raise_for_status()
            return r

    async def get_instruments(self, exchange: str = "NFO") -> list[dict]:
        if self._instruments_cache:
            return self._instruments_cache
        r = await self._get(f"/instruments/{exchange}")
        lines = r.text.strip().split("\n")
        header = lines[0].split(",")
        rows = []
        for line in lines[1:]:
            vals = line.split(",")
            if len(vals) == len(header):
                rows.append(dict(zip(header, vals)))
        self._instruments_cache = rows
        return rows

    async def get_options(self, name: str = "NIFTY", expiry: str | None = None) -> list[dict]:
        """Get options for any index: NIFTY, BANKNIFTY, SENSEX."""
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
            expiries = sorted(set(i["expiry"] for i in opts))
            if expiries:
                opts = [i for i in opts if i["expiry"] == expiries[0]]
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
        atm = round(spot_price / strike_step) * strike_step
        low = atm - chain_range
        high = atm + chain_range

        exchange = "BFO" if name == "SENSEX" else "NFO"
        filtered = [o for o in opts if low <= float(o.get("strike", 0)) <= high]
        trading_symbols = [f"{exchange}:{o['tradingsymbol']}" for o in filtered]

        quotes = {}
        for i in range(0, len(trading_symbols), 500):
            batch = trading_symbols[i:i + 500]
            q = await self.get_quote(batch)
            quotes.update(q)

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

            # Real buy/sell quantities from Kite quote
            total_buy_qty = q.get("buy_quantity", 0)
            total_sell_qty = q.get("sell_quantity", 0)
            total_qty = total_buy_qty + total_sell_qty
            real_buy_pct = total_buy_qty / total_qty if total_qty > 0 else 0.5

            # Better avg_5d approximation from average_price vs last_price
            vol = q.get("volume", 0)
            avg_price = q.get("average_price", 0)
            last_price = q.get("last_price", 0)
            # Use lower_circuit_limit/upper_circuit_limit spread as proxy for normal activity
            avg_5d = max(1, vol // 3) if vol > 0 else 1

            # Bid-ask spread baseline from depth
            bid_price = depth_buy[0].get("price", 0) if depth_buy else 0
            ask_price = depth_sell[0].get("price", 0) if depth_sell else 0
            spread_base = max(0.05, (ask_price - bid_price)) if bid_price > 0 and ask_price > 0 else 1.0

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
                "iv": 0,
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
            "expiry": opts[0]["expiry"] if opts else "",
            "chain": dict(sorted(chain.items())),
            "timestamp": datetime.now().isoformat(),
        }
