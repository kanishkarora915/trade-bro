"""TRADE BRO — Options Boom Detector. Multi-user FastAPI backend with Kite OAuth."""
import asyncio
import json
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from session_manager import session_mgr, UserSession
from kite_client import KiteClient
from data_aggregator import get_or_create_aggregator, remove_aggregator
from config import FRONTEND_URL, PORT, REFRESH_OPTION_CHAIN_SEC


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


# --- WebSocket clients per session ---
ws_clients: dict[str, set[WebSocket]] = {}
bg_tasks: dict[str, asyncio.Task] = {}


async def data_loop(session_id: str):
    """Background loop per authenticated user — runs detectors every 30s."""
    while True:
        try:
            sess = session_mgr.get_session(session_id)
            if not sess or not sess.is_authenticated:
                break

            kite = KiteClient(sess.kite_api_key, sess.kite_access_token)
            agg = get_or_create_aggregator(session_id, kite)
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
        await asyncio.sleep(REFRESH_OPTION_CHAIN_SEC)


def start_user_loop(session_id: str):
    if session_id not in bg_tasks or bg_tasks[session_id].done():
        bg_tasks[session_id] = asyncio.create_task(data_loop(session_id))


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[TRADE BRO] Backend started on port {PORT}")
    yield
    for t in bg_tasks.values():
        t.cancel()


app = FastAPI(title="TRADE BRO", lifespan=lifespan)

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
        "name": "TRADE BRO",
        "active_users": session_mgr.get_active_count(),
        "uptime": time.time(),
    }


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
    remove_aggregator(session_id)
    ws_clients.pop(session_id, None)
    session_mgr.logout(session_id)
    return {"ok": True}


# --- State REST fallback ---
@app.get("/api/state/{session_id}")
async def get_state(session_id: str):
    sess = session_mgr.get_session(session_id)
    if not sess or not sess.is_authenticated:
        raise HTTPException(403, "Not authenticated")
    kite = KiteClient(sess.kite_api_key, sess.kite_access_token)
    agg = get_or_create_aggregator(session_id, kite)
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

    try:
        # Send current state immediately
        kite = KiteClient(sess.kite_api_key, sess.kite_access_token)
        agg = get_or_create_aggregator(session_id, kite)
        state = agg.get_state()
        await ws.send_text(json.dumps(state, default=str))

        while True:
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_text("pong")
            elif msg.startswith("switch:"):
                # Switch active index: "switch:BANKNIFTY"
                idx = msg.split(":")[1].strip().upper()
                if idx in ("NIFTY", "BANKNIFTY", "SENSEX"):
                    agg.active_index = idx
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
