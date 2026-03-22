"""NSE FII/DII Data Scraper — fetches real institutional activity from NSE India.

Scrapes https://www.nseindia.com/api/fiidiiTradeReact with proper session handling.
Falls back to MoneyControl API if NSE blocks. Caches for 5 minutes.
"""

import time
import httpx

_cache: dict = {}
_CACHE_TTL = 300  # 5 minutes

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/reports-indices",
    "Connection": "keep-alive",
}


async def fetch_fii_dii() -> dict:
    """Fetch latest FII/DII data. Returns {fii_net_cr, dii_net_cr, fii_buy, fii_sell, dii_buy, dii_sell, date}.

    Values in Crores (₹).
    """
    now = time.time()
    if "data" in _cache and now - _cache.get("ts", 0) < _CACHE_TTL:
        return _cache["data"]

    data = await _fetch_nse()
    if not data:
        data = await _fetch_moneycontrol()
    if not data:
        data = {"fii_net_cr": 0, "dii_net_cr": 0, "source": "unavailable"}

    _cache["data"] = data
    _cache["ts"] = now
    return data


async def _fetch_nse() -> dict | None:
    """Fetch from NSE official API."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            # Step 1: Get session cookies from NSE homepage
            r1 = await client.get("https://www.nseindia.com", headers=NSE_HEADERS)
            cookies = r1.cookies

            # Step 2: Fetch FII/DII data
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

            fii_row = next((r for r in rows if "FII" in r.get("category", "").upper()), None)
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
    except Exception as e:
        print(f"[NSE] FII/DII fetch failed: {e}")
        return None


async def _fetch_moneycontrol() -> dict | None:
    """Fallback: fetch from MoneyControl."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.moneycontrol.com/mcapi/v1/fii-dii/activity",
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0",
                    "Accept": "application/json",
                },
            )
            if r.status_code != 200:
                return None

            data = r.json()
            # MoneyControl returns various formats — try common structure
            if isinstance(data, dict) and "data" in data:
                items = data["data"]
            elif isinstance(data, list):
                items = data
            else:
                return None

            fii_net = 0
            dii_net = 0
            for item in items if isinstance(items, list) else [items]:
                cat = str(item.get("category", "") or item.get("name", "")).upper()
                net = _parse_num(item.get("netValue", 0) or item.get("net", 0))
                if "FII" in cat or "FPI" in cat:
                    fii_net = net
                elif "DII" in cat:
                    dii_net = net

            return {
                "fii_net_cr": fii_net,
                "dii_net_cr": dii_net,
                "source": "moneycontrol",
            }
    except Exception:
        return None


def _parse_num(val) -> float:
    """Parse a number from string or float, handling commas."""
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0
