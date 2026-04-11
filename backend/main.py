"""TRADE BRO v3 — Options Boom Detector. Multi-user FastAPI backend with Kite OAuth + WebSocket Ticker."""
import asyncio
import hashlib
import json
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
import httpx
import pyotp
from session_manager import session_mgr, UserSession
from kite_client import KiteClient
from kite_ticker import KiteTicker
from data_aggregator import get_or_create_aggregator, remove_aggregator
from vpin_engine import vpin_engine
from config import FRONTEND_URL, PORT, REFRESH_OPTION_CHAIN_SEC, LICENSE_KEYS

IST = timezone(timedelta(hours=5, minutes=30))


# --- Models ---
class LicenseRequest(BaseModel):
    license_key: str

class KiteCredentials(BaseModel):
    session_id: str
    api_key: str
    api_secret: str

class KiteCallback(BaseModel):
    session_id: str
    request_token: str


# --- Per-session state ---
ws_clients: dict[str, set[WebSocket]] = {}
bg_tasks: dict[str, asyncio.Task] = {}
user_tickers: dict[str, KiteTicker] = {}  # session_id -> KiteTicker


async def data_loop(session_id: str):
    """Background loop per authenticated user — runs detectors every cycle."""
    first_run = True
    while True:
        try:
            sess = session_mgr.get_session(session_id)
            if not sess or not sess.is_authenticated:
                break

            kite = KiteClient(sess.kite_api_key, sess.kite_access_token)
            ticker = user_tickers.get(session_id)
            agg = get_or_create_aggregator(session_id, kite, ticker)
            state = await agg.run_cycle()

            msg = json.dumps(state, default=str)
            dead = set()
            for ws in ws_clients.get(session_id, set()):
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead.add(ws)
            if session_id in ws_clients:
                ws_clients[session_id] -= dead

        except Exception as e:
            print(f"[TRADE BRO] Loop error for {session_id[:8]}: {e}")

        # First run: short delay then continue. After that: normal interval.
        if first_run:
            first_run = False
            await asyncio.sleep(5)  # quick second update after 5s
        else:
            await asyncio.sleep(REFRESH_OPTION_CHAIN_SEC)


async def start_ticker(session_id: str, api_key: str, access_token: str):
    """Start Kite WebSocket ticker for a user session."""
    if session_id in user_tickers:
        return  # Already running

    ticker = KiteTicker(api_key, access_token)

    # Set up instant LTP push to frontend — ZERO LATENCY
    async def on_index_tick(index_ltp: dict):
        """Push index LTP instantly to all connected WebSocket clients."""
        tick_msg = json.dumps({"type": "tick", "index_ltp": index_ltp}, default=str)
        dead = set()
        for ws in ws_clients.get(session_id, set()):
            try:
                await ws.send_text(tick_msg)
            except Exception:
                dead.add(ws)
        if session_id in ws_clients and dead:
            ws_clients[session_id] -= dead

    ticker._on_index_tick = on_index_tick

    # VPIN feed: route all ticks to VPIN engine
    def on_vpin_tick(token: int, price: float, volume: int, oi: int = 0):
        vpin_engine.process_tick(token, price, volume, oi)
    ticker._on_vpin_tick = on_vpin_tick

    ok = await ticker.connect()
    if ok:
        # Subscribe to index tokens immediately
        await ticker.subscribe(KiteTicker.INDEX_TOKEN_LIST)
        await ticker.start()
        user_tickers[session_id] = ticker
        print(f"[TRADE BRO] Ticker started for {session_id[:8]} (index tokens subscribed)")
    else:
        print(f"[TRADE BRO] Ticker failed to connect for {session_id[:8]}")


async def stop_ticker(session_id: str):
    """Stop and remove ticker for a session."""
    ticker = user_tickers.pop(session_id, None)
    if ticker:
        await ticker.stop()
        print(f"[TRADE BRO] Ticker stopped for {session_id[:8]}")


def start_user_loop(session_id: str):
    if session_id not in bg_tasks or bg_tasks[session_id].done():
        bg_tasks[session_id] = asyncio.create_task(data_loop(session_id))


# ═══════════════════════════════════════════════════════════
#  TOTP AUTO-LOGIN (VPS headless — no browser needed)
# ═══════════════════════════════════════════════════════════
_auto_login_done_today = False
_auto_login_session_id: str | None = None

KITE_BASE = "https://api.kite.trade"

async def do_auto_login() -> tuple[bool, str]:
    """Perform automated Kite login using TOTP. Returns (success, message)."""
    global _auto_login_done_today, _auto_login_session_id
    user_id = os.environ.get("KITE_USER_ID", "")
    password = os.environ.get("KITE_PASSWORD", "")
    totp_secret = os.environ.get("KITE_TOTP_SECRET", "")
    api_key = os.environ.get("KITE_API_KEY", "")
    api_secret = os.environ.get("KITE_API_SECRET", "")
    license_key = os.environ.get("KITE_LICENSE_KEY", "KANISHK-MASTER-KEY")

    if not all([user_id, password, totp_secret, api_key, api_secret]):
        return False, "Missing KITE_* env vars for auto-login"

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            # Step 1: Login with user_id + password
            r = await client.post("https://kite.zerodha.com/api/login", data={
                "user_id": user_id, "password": password
            })
            if r.status_code != 200:
                return False, f"Login step 1 failed: HTTP {r.status_code}"
            data = r.json()
            if data.get("status") != "success":
                return False, f"Login failed: {data.get('message', 'unknown')}"
            request_id = data["data"]["request_id"]

            # Step 2: Submit TOTP
            totp_code = pyotp.TOTP(totp_secret).now()
            r = await client.post("https://kite.zerodha.com/api/twofa", data={
                "user_id": user_id, "request_id": request_id,
                "twofa_value": totp_code, "twofa_type": "totp"
            })
            if r.status_code != 200:
                return False, f"TOTP step failed: HTTP {r.status_code}"

            # Step 3: Get request_token via OAuth flow
            r = await client.get(
                f"https://kite.zerodha.com/connect/login?v=3&api_key={api_key}"
            )
            redirect_url = str(r.headers.get("location", r.url))

            parsed = urlparse(redirect_url)
            qs = parse_qs(parsed.query)
            request_token = qs.get("request_token", [None])[0]
            if not request_token:
                return False, f"No request_token in redirect: {redirect_url[:100]}"

            # Step 4: Exchange request_token for access_token
            checksum = hashlib.sha256(f"{api_key}{request_token}{api_secret}".encode()).hexdigest()
            r = await client.post(f"{KITE_BASE}/session/token", data={
                "api_key": api_key, "request_token": request_token, "checksum": checksum
            })
            d = r.json()
            if d.get("status") != "success" or not d.get("data", {}).get("access_token"):
                return False, f"Token exchange failed: {d}"

            access_token = d["data"]["access_token"]

        # Step 5: Create session via session_mgr
        result = session_mgr.create_session(license_key, "auto-login")
        session_id = result.get("session_id", "")
        if not session_id:
            return False, f"Session creation failed: {result}"

        session_mgr.set_kite_credentials(session_id, api_key, api_secret)
        session_mgr.set_access_token(session_id, access_token)

        # Step 6: Start ticker + data loop
        await start_ticker(session_id, api_key, access_token)
        start_user_loop(session_id)

        _auto_login_done_today = True
        _auto_login_session_id = session_id
        return True, f"Auto-login success — session {session_id[:8]}..."

    except Exception as e:
        return False, f"Auto-login error: {e}"


async def check_auto_login_schedule():
    """Called every 60s. Auto-login at 8:30 AM IST Mon-Fri if not already done."""
    global _auto_login_done_today
    now = datetime.now(IST)

    # Reset flag at midnight
    if now.hour == 0 and now.minute < 2:
        _auto_login_done_today = False
        return

    # Auto-login at 8:30 AM on weekdays
    if now.weekday() < 5 and now.hour == 8 and 29 <= now.minute <= 31:
        if not _auto_login_done_today:
            env_ready = all(os.environ.get(k) for k in
                           ["KITE_USER_ID", "KITE_PASSWORD", "KITE_TOTP_SECRET",
                            "KITE_API_KEY", "KITE_API_SECRET"])
            if env_ready:
                print("[TRADE BRO] Auto-login triggered (8:30 AM schedule)...")
                success, msg = await do_auto_login()
                print(f"[TRADE BRO] Auto-login result: {msg}")


async def auto_login_scheduler():
    """Background task that checks auto-login every 60 seconds."""
    while True:
        try:
            await check_auto_login_schedule()
        except Exception as e:
            print(f"[TRADE BRO] Auto-login scheduler error: {e}")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[TRADE BRO] Backend v3 started on port {PORT}")
    env_auto = all(os.environ.get(k) for k in
                   ["KITE_USER_ID", "KITE_PASSWORD", "KITE_TOTP_SECRET",
                    "KITE_API_KEY", "KITE_API_SECRET"])
    print(f"[TRADE BRO] Auto-Login: {'ENABLED' if env_auto else 'DISABLED (set KITE_* env vars)'}")
    # Register NIFTY futures for VPIN (index token 256 receives NIFTY 50 ticks)
    vpin_engine.register_futures(256, "NIFTY-FUT")
    print("[TRADE BRO] VPIN: NIFTY-FUT registered. CE/PE sides register on first chain build.")
    print("[TRADE BRO] Ready — instruments will cache on first user login")

    # Start auto-login scheduler
    scheduler_task = asyncio.create_task(auto_login_scheduler())

    # Auto-login on startup if market hours and env vars present
    if env_auto:
        now = datetime.now(IST)
        if now.weekday() < 5 and 8 <= now.hour < 16:
            print("[TRADE BRO] Auto-login on startup (market hours)...")
            success, msg = await do_auto_login()
            print(f"[TRADE BRO] Startup auto-login: {msg}")

    yield
    scheduler_task.cancel()
    for t in bg_tasks.values():
        t.cancel()
    for sid in list(user_tickers.keys()):
        await stop_ticker(sid)


app = FastAPI(title="TRADE BRO", lifespan=lifespan)

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health ---
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "name": "TRADE BRO v3",
        "active_users": session_mgr.get_active_count(),
        "active_tickers": len(user_tickers),
        "uptime": time.time(),
    }


# --- Auto-Login (TOTP) ---
class AutoLoginRequest(BaseModel):
    master_key: str

@app.post("/api/autologin")
async def autologin(req: AutoLoginRequest):
    if req.master_key != "KANISHK-MASTER-KEY":
        raise HTTPException(403, "Invalid master key")
    success, msg = await do_auto_login()
    return {"success": success, "message": msg}


# --- VPIN ---
@app.get("/api/vpin")
async def get_vpin():
    return vpin_engine.get_all_states()

@app.get("/api/vpin/{token}/history")
async def get_vpin_history(token: int):
    history = vpin_engine.get_history(token)
    if not history:
        return {"token": token, "buckets": [], "count": 0}
    return {"token": token, "buckets": history, "count": len(history)}


# --- Trade Reports ---
@app.get("/api/reports/daily")
async def report_daily():
    from trade_tracker import get_daily_report
    return get_daily_report()

@app.get("/api/reports/weekly")
async def report_weekly():
    from trade_tracker import get_weekly_report
    return get_weekly_report()

@app.get("/api/reports/monthly")
async def report_monthly():
    from trade_tracker import get_monthly_report
    return get_monthly_report()


# --- Debug chain ---
@app.get("/api/debug/chain")
async def debug_chain():
    """Debug endpoint to diagnose why chain is empty."""
    from data_aggregator import user_aggregators
    debug = {"aggregators": len(user_aggregators), "sessions": []}
    for sid, agg in user_aggregators.items():
        active = agg.indices.get(agg.active_index)
        sess_info = {
            "session_id": sid[:8],
            "active_index": agg.active_index,
            "spot": active.spot if active else 0,
            "atm": active.atm if active else 0,
            "chain_len": len(active.chain) if active else 0,
            "chain_summary_len": len(active._chain_summary()) if active else 0,
            "strike_map_len": len(active.strike_map) if active else 0,
            "error": active.error if active else "",
            "last_fetch": active.last_fetch if active else 0,
            "detectors_count": len(active.detectors) if active else 0,
            "vix": agg.india_vix,
        }
        debug["sessions"].append(sess_info)

    # Try a fresh instruments + options check
    try:
        for sid, agg in user_aggregators.items():
            kite = agg.kite
            from datetime import datetime
            today_str = datetime.now().strftime("%Y-%m-%d")

            # Check instruments — raw CSV analysis
            instruments = await kite.get_instruments("NFO")
            debug["instruments_total"] = len(instruments)
            debug["today"] = today_str

            # Show CSV headers (column names from first instrument)
            if instruments:
                debug["csv_columns"] = list(instruments[0].keys())
                # Sample first instrument
                debug["sample_instrument"] = instruments[0]

            # Check all unique values for key fields
            all_names = set(i.get("name", "") for i in instruments)
            all_types = set(i.get("instrument_type", "") for i in instruments)
            all_segments = set(i.get("segment", "") for i in instruments)

            # Find NIFTY-related names
            nifty_names = [n for n in all_names if "NIFTY" in n.upper()] if all_names else []
            debug["nifty_related_names"] = sorted(nifty_names)[:10]
            debug["all_instrument_types"] = sorted(list(all_types))[:10]
            debug["all_segments"] = sorted(list(all_segments))[:10]

            # Try different filters to find NIFTY options
            by_name = [i for i in instruments if i.get("name") == "NIFTY"]
            by_name_upper = [i for i in instruments if i.get("name", "").upper() == "NIFTY"]
            by_name_contains = [i for i in instruments if "NIFTY" in i.get("name", "").upper()]
            by_tradingsymbol = [i for i in instruments if i.get("tradingsymbol", "").startswith("NIFTY")]

            debug["filter_name_exact"] = len(by_name)
            debug["filter_name_upper"] = len(by_name_upper)
            debug["filter_name_contains"] = len(by_name_contains)
            debug["filter_tradingsymbol_starts"] = len(by_tradingsymbol)

            # Show sample NIFTY option if found via tradingsymbol
            nifty_by_ts = [i for i in by_tradingsymbol if i.get("instrument_type") in ("CE", "PE")]
            if not nifty_by_ts:
                # Try case-insensitive
                nifty_by_ts = [i for i in by_tradingsymbol if i.get("instrument_type", "").upper() in ("CE", "PE")]
            debug["nifty_options_via_tradingsymbol"] = len(nifty_by_ts)
            if nifty_by_ts:
                debug["sample_nifty_option"] = nifty_by_ts[0]

            # Full filter match
            nifty_opts = [i for i in instruments if i.get("name") == "NIFTY" and i.get("instrument_type") in ("CE", "PE") and i.get("segment") == "NFO-OPT"]
            debug["nifty_options_full_filter"] = len(nifty_opts)

            break
    except Exception as e:
        debug["debug_error"] = str(e)[:300]

    return debug


# --- License ---
@app.post("/api/license/verify")
async def verify_license(req: LicenseRequest, request: Request):
    ip = request.client.host if request.client else ""
    result = session_mgr.create_session(req.license_key, ip)
    return result


# --- Kite Auth ---
@app.post("/api/kite/credentials")
async def set_kite_credentials(req: KiteCredentials):
    ok = session_mgr.set_kite_credentials(req.session_id, req.api_key, req.api_secret)
    if not ok:
        raise HTTPException(400, "Invalid session")
    login_url = KiteClient.get_login_url(req.api_key)
    return {"login_url": login_url}


@app.post("/api/kite/callback")
async def kite_callback(req: KiteCallback):
    sess = session_mgr.get_session(req.session_id)
    if not sess:
        raise HTTPException(400, "Invalid session")
    if not sess.kite_api_key or not sess.kite_api_secret:
        raise HTTPException(400, "API credentials not set")

    result = await KiteClient.generate_session(
        sess.kite_api_key, sess.kite_api_secret, req.request_token
    )
    if "error" in result:
        raise HTTPException(400, f"Kite auth failed: {result['error']}")

    session_mgr.set_access_token(sess.session_id, result["access_token"])

    # Start Kite WebSocket ticker for real-time tick data
    await start_ticker(sess.session_id, sess.kite_api_key, result["access_token"])

    # Start data loop for this user
    start_user_loop(sess.session_id)

    return {
        "authenticated": True,
        "user_id": result.get("user_id", ""),
        "user_name": result.get("user_name", ""),
        "session": sess.to_dict(),
    }


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    sess = session_mgr.get_session(session_id)
    if not sess:
        raise HTTPException(404, "Session not found")
    return sess.to_dict()


@app.post("/api/logout/{session_id}")
async def logout(session_id: str):
    task = bg_tasks.pop(session_id, None)
    if task:
        task.cancel()
    await stop_ticker(session_id)
    remove_aggregator(session_id)
    ws_clients.pop(session_id, None)
    session_mgr.logout(session_id)
    return {"ok": True}


# --- Switch Expiry ---
class SwitchExpiryRequest(BaseModel):
    session_id: str
    expiry: str  # "2026-04-03" or "" for nearest

@app.post("/api/expiry/switch")
async def switch_expiry(req: SwitchExpiryRequest):
    sess = session_mgr.get_session(req.session_id)
    if not sess or not sess.is_authenticated:
        raise HTTPException(403, "Not authenticated")
    kite = KiteClient(sess.kite_api_key, sess.kite_access_token)
    ticker = user_tickers.get(req.session_id)
    agg = get_or_create_aggregator(req.session_id, kite, ticker)
    # Set selected expiry on aggregator
    agg.selected_expiry = req.expiry if req.expiry else None
    # Force chain rebuild
    idx = agg.active_index
    agg._cache.pop(f"chain_{idx}", None)
    try:
        state = await agg.run_cycle(idx)
    except Exception:
        state = agg.get_state()
    return state

@app.get("/api/expiries/{session_id}")
async def get_expiries(session_id: str):
    sess = session_mgr.get_session(session_id)
    if not sess or not sess.is_authenticated:
        raise HTTPException(403, "Not authenticated")
    kite = KiteClient(sess.kite_api_key, sess.kite_access_token)
    agg = get_or_create_aggregator(session_id, kite, user_tickers.get(session_id))
    idx = agg.active_index
    cfg = agg.indices[idx].cfg
    exchange = "BFO" if cfg["name"] == "SENSEX" else "NFO"
    instruments = await kite.get_instruments(exchange)
    segment = f"{exchange}-OPT"
    opts = [i for i in instruments if i.get("name") == cfg["name"] and i.get("instrument_type") in ("CE", "PE") and i.get("segment") == segment]
    today_str = datetime.now(IST).strftime("%Y-%m-%d")
    expiries = sorted(set(i["expiry"] for i in opts if i["expiry"] >= today_str))
    return {"expiries": expiries[:12], "current": getattr(agg, 'selected_expiry', None) or (expiries[0] if expiries else "")}


# --- VIX Toggle ---
@app.post("/api/vix/toggle/{session_id}")
async def toggle_vix(session_id: str):
    """Toggle India VIX integration on/off."""
    sess = session_mgr.get_session(session_id)
    if not sess or not sess.is_authenticated:
        raise HTTPException(403, "Not authenticated")
    kite = KiteClient(sess.kite_api_key, sess.kite_access_token)
    ticker = user_tickers.get(session_id)
    agg = get_or_create_aggregator(session_id, kite, ticker)
    agg.vix_enabled = not agg.vix_enabled
    return {"vix_enabled": agg.vix_enabled}


# --- Data Management ---
@app.delete("/api/data/signals/{session_id}")
async def clear_today_signals(session_id: str):
    """Clear today's signal history."""
    sess = session_mgr.get_session(session_id)
    if not sess or not sess.is_authenticated:
        raise HTTPException(403, "Not authenticated")
    kite = KiteClient(sess.kite_api_key, sess.kite_access_token)
    ticker = user_tickers.get(session_id)
    agg = get_or_create_aggregator(session_id, kite, ticker)
    from datetime import datetime, timezone, timedelta
    today = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d")
    agg.signal_history = []
    agg.last_signal = None
    agg.data_store.save_signals(today, [])
    return {"cleared": "signals", "date": today}


@app.delete("/api/data/all/{session_id}")
async def clear_all_data(session_id: str):
    """Clear all saved data (signals + snapshots + levels)."""
    sess = session_mgr.get_session(session_id)
    if not sess or not sess.is_authenticated:
        raise HTTPException(403, "Not authenticated")
    kite = KiteClient(sess.kite_api_key, sess.kite_access_token)
    ticker = user_tickers.get(session_id)
    agg = get_or_create_aggregator(session_id, kite, ticker)
    agg.signal_history = []
    agg.last_signal = None
    agg.alert_log = []
    import shutil, os
    data_dir = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
    for sub in ["signals", "daily", "levels"]:
        p = os.path.join(data_dir, sub)
        if os.path.exists(p):
            shutil.rmtree(p)
            os.makedirs(p, exist_ok=True)
    return {"cleared": "all"}


# --- State REST fallback ---
@app.get("/api/state/{session_id}")
async def get_state(session_id: str):
    sess = session_mgr.get_session(session_id)
    if not sess or not sess.is_authenticated:
        raise HTTPException(403, "Not authenticated")
    kite = KiteClient(sess.kite_api_key, sess.kite_access_token)
    ticker = user_tickers.get(session_id)
    agg = get_or_create_aggregator(session_id, kite, ticker)
    return agg.get_state()


# --- WebSocket ---
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(ws: WebSocket, session_id: str):
    sess = session_mgr.get_session(session_id)
    if not sess or not sess.is_authenticated:
        await ws.close(code=4001, reason="Not authenticated")
        return

    await ws.accept()
    if session_id not in ws_clients:
        ws_clients[session_id] = set()
    ws_clients[session_id].add(ws)

    # Ensure data loop is running
    start_user_loop(session_id)

    # Ensure ticker is running
    if session_id not in user_tickers and sess.kite_access_token:
        await start_ticker(session_id, sess.kite_api_key, sess.kite_access_token)

    try:
        # Run first cycle IMMEDIATELY so user doesn't see empty dashboard
        kite = KiteClient(sess.kite_api_key, sess.kite_access_token)
        ticker = user_tickers.get(session_id)
        agg = get_or_create_aggregator(session_id, kite, ticker)
        state = agg.get_state()
        if state.get("spot", 0) == 0:
            # No data yet — run cycle right now instead of waiting for background loop
            try:
                state = await agg.run_cycle()
            except Exception as e:
                print(f"[WS] First cycle error: {e}")
                state = agg.get_state()
        await ws.send_text(json.dumps(state, default=str))

        while True:
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_text("pong")
            elif msg.startswith("switch:"):
                idx = msg.split(":")[1].strip().upper()
                if idx in ("NIFTY", "BANKNIFTY", "SENSEX"):
                    agg.active_index = idx
                    # If this index has no chain data, build it immediately
                    idx_state = agg.indices.get(idx)
                    if idx_state and len(idx_state.chain) == 0:
                        try:
                            state = await agg.run_cycle(idx)
                        except Exception as e:
                            print(f"[WS] Switch cycle error for {idx}: {e}")
                            state = agg.get_state()
                    else:
                        state = agg.get_state()
                    await ws.send_text(json.dumps(state, default=str))
            elif msg.startswith("expiry:"):
                exp = msg.split(":", 1)[1].strip()
                agg.selected_expiry = exp if exp else None
                agg._cache.pop(f"chain_{agg.active_index}", None)
                try:
                    state = await agg.run_cycle(agg.active_index)
                except Exception:
                    state = agg.get_state()
                await ws.send_text(json.dumps(state, default=str))
            elif msg == "toggle_vix":
                agg.vix_enabled = not agg.vix_enabled
                state = agg.get_state()
                await ws.send_text(json.dumps(state, default=str))
    except WebSocketDisconnect:
        pass
    finally:
        if session_id in ws_clients:
            ws_clients[session_id].discard(ws)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
