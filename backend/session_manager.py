"""Multi-user session manager for TRADE BRO. Each user has their own Kite session.
Sessions persist to disk so they survive Render deploys/restarts.
"""
import json
import os
import secrets
import time
import hashlib
from datetime import datetime
from config import LICENSE_KEYS, MAX_SESSIONS, SESSION_TIMEOUT_HOURS

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")


class UserSession:
    __slots__ = (
        "session_id", "license_key", "user_name",
        "kite_api_key", "kite_api_secret", "kite_access_token",
        "created_at", "last_active", "ip_address",
    )

    def __init__(self, license_key: str, user_name: str, ip: str = ""):
        self.session_id = secrets.token_hex(24)
        self.license_key = license_key
        self.user_name = user_name
        self.kite_api_key = ""
        self.kite_api_secret = ""
        self.kite_access_token = ""
        self.created_at = time.time()
        self.last_active = time.time()
        self.ip_address = ip

    @property
    def is_authenticated(self) -> bool:
        return bool(self.kite_access_token)

    @property
    def age_hours(self) -> float:
        return (time.time() - self.created_at) / 3600

    def touch(self):
        self.last_active = time.time()

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_name": self.user_name,
            "is_authenticated": self.is_authenticated,
            "has_api_key": bool(self.kite_api_key),
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "ip": self.ip_address,
        }

    def to_json(self) -> dict:
        """Full serialization for disk persistence."""
        return {
            "session_id": self.session_id,
            "license_key": self.license_key,
            "user_name": self.user_name,
            "kite_api_key": self.kite_api_key,
            "kite_api_secret": self.kite_api_secret,
            "kite_access_token": self.kite_access_token,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "ip_address": self.ip_address,
        }

    @classmethod
    def from_json(cls, data: dict) -> 'UserSession':
        """Restore session from disk."""
        sess = cls.__new__(cls)
        sess.session_id = data["session_id"]
        sess.license_key = data["license_key"]
        sess.user_name = data["user_name"]
        sess.kite_api_key = data.get("kite_api_key", "")
        sess.kite_api_secret = data.get("kite_api_secret", "")
        sess.kite_access_token = data.get("kite_access_token", "")
        sess.created_at = data.get("created_at", time.time())
        sess.last_active = data.get("last_active", time.time())
        sess.ip_address = data.get("ip_address", "")
        return sess


class SessionManager:
    def __init__(self):
        self.sessions: dict[str, UserSession] = {}  # session_id -> UserSession
        self._license_sessions: dict[str, str] = {}  # license_key -> session_id
        self._load_from_disk()

    def _save_to_disk(self):
        """Persist all sessions to disk."""
        try:
            os.makedirs(os.path.dirname(SESSIONS_FILE), exist_ok=True)
            data = [s.to_json() for s in self.sessions.values()]
            with open(SESSIONS_FILE, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"[SESSION] Save error: {e}")

    def _load_from_disk(self):
        """Restore sessions from disk on startup."""
        try:
            if os.path.exists(SESSIONS_FILE):
                with open(SESSIONS_FILE, "r") as f:
                    data = json.load(f)
                count = 0
                for item in data:
                    sess = UserSession.from_json(item)
                    # Skip expired sessions (older than timeout)
                    if sess.age_hours > SESSION_TIMEOUT_HOURS:
                        continue
                    self.sessions[sess.session_id] = sess
                    self._license_sessions[sess.license_key] = sess.session_id
                    count += 1
                if count:
                    print(f"[SESSION] Restored {count} sessions from disk")
        except Exception as e:
            print(f"[SESSION] Load error: {e}")

    def verify_license(self, key: str) -> dict:
        key = key.strip().upper()
        info = LICENSE_KEYS.get(key)
        if not info:
            return {"valid": False, "error": "Invalid license key"}
        if not info.get("active"):
            return {"valid": False, "error": "License key deactivated"}
        return {"valid": True, "name": info["name"]}

    def create_session(self, license_key: str, ip: str = "") -> dict:
        key = license_key.strip().upper()
        check = self.verify_license(key)
        if not check["valid"]:
            return check

        # Clean expired sessions
        self._cleanup()

        # Check if this license already has a session
        if key in self._license_sessions:
            old_sid = self._license_sessions[key]
            if old_sid in self.sessions:
                # Reuse existing session
                sess = self.sessions[old_sid]
                sess.touch()
                sess.ip_address = ip
                return {"valid": True, "session": sess.to_dict()}

        if len(self.sessions) >= MAX_SESSIONS:
            return {"valid": False, "error": "Max users reached. Try later."}

        sess = UserSession(key, check["name"], ip)
        self.sessions[sess.session_id] = sess
        self._license_sessions[key] = sess.session_id
        self._save_to_disk()
        return {"valid": True, "session": sess.to_dict()}

    def get_session(self, session_id: str) -> UserSession | None:
        sess = self.sessions.get(session_id)
        if sess:
            sess.touch()
        return sess

    def set_kite_credentials(self, session_id: str, api_key: str, api_secret: str) -> bool:
        sess = self.sessions.get(session_id)
        if not sess:
            return False
        sess.kite_api_key = api_key
        sess.kite_api_secret = api_secret
        sess.touch()
        self._save_to_disk()
        return True

    def set_access_token(self, session_id: str, access_token: str) -> bool:
        sess = self.sessions.get(session_id)
        if not sess:
            return False
        sess.kite_access_token = access_token
        sess.touch()
        self._save_to_disk()
        return True

    def logout(self, session_id: str):
        sess = self.sessions.pop(session_id, None)
        if sess:
            self._license_sessions.pop(sess.license_key, None)
        self._save_to_disk()

    def get_active_count(self) -> int:
        return len(self.sessions)

    def _cleanup(self):
        expired = [
            sid for sid, sess in self.sessions.items()
            if sess.age_hours > SESSION_TIMEOUT_HOURS
        ]
        for sid in expired:
            sess = self.sessions.pop(sid, None)
            if sess:
                self._license_sessions.pop(sess.license_key, None)


session_mgr = SessionManager()
