"""Multi-user session manager for TRADE BRO. Each user has their own Kite session."""
import secrets
import time
import hashlib
from datetime import datetime
from config import LICENSE_KEYS, MAX_SESSIONS, SESSION_TIMEOUT_HOURS


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


class SessionManager:
    def __init__(self):
        self.sessions: dict[str, UserSession] = {}  # session_id -> UserSession
        self._license_sessions: dict[str, str] = {}  # license_key -> session_id

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
        return True

    def set_access_token(self, session_id: str, access_token: str) -> bool:
        sess = self.sessions.get(session_id)
        if not sess:
            return False
        sess.kite_access_token = access_token
        sess.touch()
        return True

    def logout(self, session_id: str):
        sess = self.sessions.pop(session_id, None)
        if sess:
            self._license_sessions.pop(sess.license_key, None)

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
