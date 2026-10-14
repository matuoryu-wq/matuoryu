"""アプリ本体: 認証・監査ログ・静的ファイル配信。API は api.py。"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import logging
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import backup, db
from .config import Settings, load_settings

log = logging.getLogger("case_manager")
STATIC_DIR = Path(__file__).parent / "static"
COOKIE = "cm_session"
PUBLIC_API = {"/api/auth/login", "/api/health"}


@dataclass
class SessionInfo:
    key: str          # 監査ログ用の短い識別子(トークン自体ではない)
    id_hash: str | None
    reauth_at: dt.datetime | None
    reauth_minutes: int

    @property
    def reauth_ok(self) -> bool:
        if self.reauth_at is None:
            return False
        return dt.datetime.now() - self.reauth_at <= dt.timedelta(minutes=self.reauth_minutes)


def _hash(v: str) -> str:
    return hashlib.sha256(v.encode()).hexdigest()


def audit(conn, request: Request | None, action: str, entity: str = "", entity_id: int | None = None,
          case_id: int | None = None, detail: dict | str | None = None) -> None:
    sess = getattr(request.state, "session", None) if request else None
    ip = ""
    if request:
        ip = request.headers.get("x-forwarded-for", "") or (request.client.host if request.client else "")
        who = request.headers.get("tailscale-user-login", "")
        if who:
            ip = f"{ip} ({who})"
    if isinstance(detail, dict):
        detail = json.dumps(detail, ensure_ascii=False)
    conn.execute(
        "INSERT INTO audit_log(ts,session,ip,action,entity,entity_id,case_id,detail) VALUES(?,?,?,?,?,?,?,?)",
        (db.now(), sess.key if sess else "", ip, action, entity, entity_id, case_id, detail or ""),
    )


class LoginLimiter:
    """ログイン失敗の連続を制限(単一利用者想定のため全体で数える)。"""

    def __init__(self, max_fail: int = 5, window: int = 600):
        self.max_fail, self.window = max_fail, window
        self.fails: list[float] = []

    def blocked(self) -> bool:
        t = time.time()
        self.fails = [f for f in self.fails if t - f < self.window]
        return len(self.fails) >= self.max_fail

    def fail(self) -> None:
        self.fails.append(time.time())

    def reset(self) -> None:
        self.fails.clear()


def create_app(settings: Settings | None = None, start_background: bool = False) -> FastAPI:
    settings = settings or load_settings()
    if not settings.app_token or len(settings.app_token) < 16:
        raise RuntimeError("APP_TOKEN が未設定か短すぎます(16文字以上)。.env を確認してください。")

    conn = db.connect(settings.db_path)
    db.init_db(conn)
    conn.close()

    app = FastAPI(title="案件管理", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.limiter = LoginLimiter()

    @app.middleware("http")
    async def security(request: Request, call_next):
        path = request.url.path
        request.state.session = None
        if path.startswith("/api/") and path not in PUBLIC_API:
            sess = _resolve_session(request, settings)
            if sess is None:
                return JSONResponse({"detail": "認証が必要です"}, status_code=401)
            request.state.session = sess
            if request.method not in ("GET", "HEAD") and request.headers.get("x-cm") != "1":
                return JSONResponse({"detail": "不正なリクエストです(CSRF)"}, status_code=403)
        elif path == "/api/auth/login" and request.headers.get("x-cm") != "1":
            return JSONResponse({"detail": "不正なリクエストです(CSRF)"}, status_code=403)

        response: Response = await call_next(request)

        # 操作ログ: 変更系 API はすべて記録
        if path.startswith("/api/") and request.method not in ("GET", "HEAD") and path != "/api/auth/login":
            c = db.connect(settings.db_path)
            try:
                audit(c, request, f"{request.method} {path}", detail={"status": response.status_code})
            finally:
                c.close()

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        if path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    from .api import router
    app.include_router(router)

    @app.get("/api/health")
    def health():
        return {"ok": True}

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})

    @app.get("/sw.js")
    def sw():
        return FileResponse(STATIC_DIR / "sw.js", media_type="text/javascript",
                            headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})

    @app.get("/manifest.webmanifest")
    def manifest():
        return FileResponse(STATIC_DIR / "manifest.webmanifest", media_type="application/manifest+json")

    if start_background:
        backup.start_scheduler(settings.db_path, settings.backup_dir, settings.backup_keep)
    return app


def _resolve_session(request: Request, settings: Settings) -> SessionInfo | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        if hmac.compare_digest(auth[7:].strip().encode(), settings.app_token.encode()):
            return SessionInfo("bearer", None, dt.datetime.now(), settings.reauth_minutes)
        return None
    sid = request.cookies.get(COOKIE)
    if not sid:
        return None
    h = _hash(sid)
    conn = db.connect(settings.db_path)
    try:
        r = conn.execute("SELECT * FROM sessions WHERE id_hash=?", (h,)).fetchone()
        if not r:
            return None
        created = dt.datetime.fromisoformat(r["created_at"])
        if dt.datetime.now() - created > dt.timedelta(hours=settings.session_hours):
            conn.execute("DELETE FROM sessions WHERE id_hash=?", (h,))
            return None
        conn.execute("UPDATE sessions SET last_seen=? WHERE id_hash=?", (db.now(), h))
        reauth = dt.datetime.fromisoformat(r["reauth_at"]) if r["reauth_at"] else None
        return SessionInfo(h[:10], h, reauth, settings.reauth_minutes)
    finally:
        conn.close()


def new_session(conn, request: Request) -> str:
    sid = secrets.token_urlsafe(32)
    t = db.now()
    conn.execute("INSERT INTO sessions(id_hash,created_at,last_seen,reauth_at,user_agent) VALUES(?,?,?,?,?)",
                 (_hash(sid), t, t, t, request.headers.get("user-agent", "")[:200]))
    return sid


def check_token(settings: Settings, token: str) -> bool:
    return bool(token) and hmac.compare_digest(token.encode(), settings.app_token.encode())
