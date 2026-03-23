"""NSE FII/DII Data Scraper — fetches real institutional activity.

Multiple fallback sources:
1. NSE India API (needs Indian IP — may fail on US servers)
2. Trendlyne public API
3. NSDL depositories
4. Groww/Tickertape public data
Caches for 5 minutes.
"""

import time
import httpx

_cache: dict = {}
_CACHE_TTL = 300  # 5 minutes

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/reports-indices",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}


async def fetch_fii_dii() -> dict:
    """Fetch latest FII/DII data. Tries multiple sources.

    Returns {fii_net_cr, dii_net_cr, fii_buy, fii_sell, dii_buy, dii_sell, date, source}.
    Values in Crores (₹).
    """
    now = time.time()
    if "data" in _cache and now - _cache.get("ts", 0) < _CACHE_TTL:
        cached = _cache["data"]
        if cached.get("fii_net_cr", 0) != 0 or cached.get("dii_net_cr", 0) != 0:
            return cached

    # Try sources in order of reliability
    sources = [_fetch_nse, _fetch_trendlyne, _fetch_groww, _fetch_moneycontrol]
    for fetch_fn in sources:
        try:
            data = await fetch_fn()
            if data and (data.get("fii_net_cr", 0) != 0 or data.get("dii_net_cr", 0) != 0):
                _cache["data"] = data
                _cache["ts"] = now
                print(f"[FII/DII] Got data from {data.get('source', '?')}: FII={data['fii_net_cr']:.0f}Cr DII={data['dii_net_cr']:.0f}Cr")
                return data
        except Exception as e:
            print(f"[FII/DII] {fetch_fn.__name__} failed: {e}")
            continue

    fallback = {"fii_net_cr": 0, "dii_net_cr": 0, "source": "unavailable"}
    _cache["data"] = fallback
    _cache["ts"] = now
    return fallback


async def _fetch_nse() -> dict | None:
    """Fetch from NSE official API (works best from Indian IPs)."""
    async with httpx.AsyncClient(timeout=8, follow_redirects=True, verify=False) as client:
        # Get session cookies
        r1 = await client.get("https://www.nseindia.com", headers=NSE_HEADERS)
        cookies = r1.cookies

        # FII/DII data
        r2 = await client.get(
            "https://www.nseindia.com/api/fiidiiTradeReact",
            headers=NSE_HEADERS,
            cookies=cookies,
        )
        if r2.status_code != 200:
            return None

        rows = r2.json()
        if not isinstance(rows, list) or len(rows) < 2:
            return None

        fii_row = next((r for r in rows if "FII" in r.get("category", "").upper() or "FPI" in r.get("category", "").upper()), None)
        dii_row = next((r for r in rows if "DII" in r.get("category", "").upper()), None)

        if not fii_row or not dii_row:
            return None

        return {
            "fii_net_cr": _parse_num(fii_row.get("netValue", "0")),
            "dii_net_cr": _parse_num(dii_row.get("netValue", "0")),
            "fii_buy": _parse_num(fii_row.get("buyValue", "0")),
            "fii_sell": _parse_num(fii_row.get("sellValue", "0")),
            "dii_buy": _parse_num(dii_row.get("buyValue", "0")),
            "dii_sell": _parse_num(dii_row.get("sellValue", "0")),
            "date": fii_row.get("date", ""),
            "source": "nse",
        }


async def _fetch_trendlyne() -> dict | None:
    """Fetch from Trendlyne public API."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/122.0.0.0",
        "Accept": "application/json",
        "Referer": "https://trendlyne.com/",
    }
    async with httpx.AsyncClient(timeout=8) as client:
        r = await client.get("https://trendlyne.com/fundamentals/fii-activity-json/", headers=headers)
        if r.status_code != 200:
            return None
        data = r.json()
        if isinstance(data, dict):
            return {
                "fii_net_cr": _parse_num(data.get("fii_net", 0) or data.get("fpi_net", 0)),
                "dii_net_cr": _parse_num(data.get("dii_net", 0)),
                "fii_buy": _parse_num(data.get("fii_buy", 0) or data.get("fpi_buy", 0)),
                "fii_sell": _parse_num(data.get("fii_sell", 0) or data.get("fpi_sell", 0)),
                "dii_buy": _parse_num(data.get("dii_buy", 0)),
                "dii_sell": _parse_num(data.get("dii_sell", 0)),
                "date": data.get("date", ""),
                "source": "trendlyne",
            }
    return None


async def _fetch_groww() -> dict | None:
    """Fetch from Groww public API."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/122.0.0.0",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=8) as client:
        r = await client.get("https://groww.in/v1/api/stocks_data/v2/fii_dii_activity/cash", headers=headers)
        if r.status_code != 200:
            return None
        data = r.json()
        if isinstance(data, dict):
            fii = data.get("fiiActivity", {}) or data.get("fpiActivity", {})
            dii = data.get("diiActivity", {})
            fii_buy = _parse_num(fii.get("buyValue", 0))
            fii_sell = _parse_num(fii.get("sellValue", 0))
            dii_buy = _parse_num(dii.get("buyValue", 0))
            dii_sell = _parse_num(dii.get("sellValue", 0))
            return {
                "fii_net_cr": fii_buy - fii_sell,
                "dii_net_cr": dii_buy - dii_sell,
                "fii_buy": fii_buy,
                "fii_sell": fii_sell,
                "dii_buy": dii_buy,
                "dii_sell": dii_sell,
                "date": data.get("date", ""),
                "source": "groww",
            }
    return None


async def _fetch_moneycontrol() -> dict | None:
    """Fallback: fetch from MoneyControl."""
    async with httpx.AsyncClient(timeout=8) as client:
        r = await client.get(
            "https://api.moneycontrol.com/mcapi/v1/fii-dii/overview",
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/122.0.0.0",
                "Accept": "application/json",
            },
        )
        if r.status_code != 200:
            return None

        data = r.json()
        result = {"fii_net_cr": 0, "dii_net_cr": 0, "source": "moneycontrol"}

        # Navigate MoneyControl's response
        if isinstance(data, dict):
            items = data.get("data", data)
            if isinstance(items, list):
                for item in items:
                    cat = str(item.get("category", "") or item.get("name", "")).upper()
                    net = _parse_num(item.get("netValue", 0) or item.get("net", 0))
                    buy = _parse_num(item.get("buyValue", 0) or item.get("buy", 0))
                    sell = _parse_num(item.get("sellValue", 0) or item.get("sell", 0))
                    if "FII" in cat or "FPI" in cat:
                        result["fii_net_cr"] = net if net != 0 else buy - sell
                        result["fii_buy"] = buy
                        result["fii_sell"] = sell
                    elif "DII" in cat:
                        result["dii_net_cr"] = net if net != 0 else buy - sell
                        result["dii_buy"] = buy
                        result["dii_sell"] = sell

        if result["fii_net_cr"] != 0 or result["dii_net_cr"] != 0:
            return result
    return None


def _parse_num(val) -> float:
    """Parse a number from string or float, handling commas."""
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0
