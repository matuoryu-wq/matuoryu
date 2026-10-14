"""設定読込。秘密情報は .env からのみ読み、画面・ログには出さない。"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEYS = ("APP_TOKEN", "ANTHROPIC_API_KEY")


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        values[key.strip()] = val
    return values


@dataclass
class Settings:
    app_token: str
    port: int = 8765
    data_dir: Path = BASE_DIR / "data"
    backup_dir: Path | None = None
    backup_keep: int = 30
    allowed_folder_roots: list[Path] = field(default_factory=list)
    reauth_minutes: int = 10
    session_hours: int = 720

    @property
    def db_path(self) -> Path:
        return self.data_dir / "cases.sqlite3"


def load_settings(env_file: Path | None = None, overrides: dict[str, str] | None = None) -> Settings:
    env = _load_env_file(env_file or BASE_DIR / ".env")
    # 環境変数が優先(テスト・サービス化用)
    for k in list(env) + ["APP_TOKEN", "APP_PORT", "DATA_DIR", "BACKUP_DIR", "BACKUP_KEEP",
                          "ALLOWED_FOLDER_ROOTS", "REAUTH_MINUTES", "SESSION_HOURS"]:
        if k in os.environ:
            env[k] = os.environ[k]
    if overrides:
        env.update(overrides)

    def path_of(v: str) -> Path:
        p = Path(v)
        return p if p.is_absolute() else (BASE_DIR / p).resolve()

    roots = [path_of(r.strip()) for r in env.get("ALLOWED_FOLDER_ROOTS", "").split(";") if r.strip()]
    return Settings(
        app_token=env.get("APP_TOKEN", ""),
        port=int(env.get("APP_PORT") or 8765),
        data_dir=path_of(env.get("DATA_DIR") or "data"),
        backup_dir=path_of(env["BACKUP_DIR"]) if env.get("BACKUP_DIR") else None,
        backup_keep=int(env.get("BACKUP_KEEP") or 30),
        allowed_folder_roots=roots,
        reauth_minutes=int(env.get("REAUTH_MINUTES") or 10),
        session_hours=int(env.get("SESSION_HOURS") or 720),
    )


class RedactSecretsFilter(logging.Filter):
    """ログ出力から秘密値(トークン・APIキー)を伏せる。"""

    def __init__(self, secrets: list[str]):
        super().__init__()
        self.secrets = [s for s in secrets if s and len(s) >= 6]

    def filter(self, record: logging.LogRecord) -> bool:
        if self.secrets:
            msg = record.getMessage()
            redacted = msg
            for s in self.secrets:
                redacted = redacted.replace(s, "***")
            if redacted != msg:
                record.msg, record.args = redacted, ()
        return True


def install_log_redaction() -> None:
    env = _load_env_file(BASE_DIR / ".env")
    secrets = [os.environ.get(k) or env.get(k, "") for k in SECRET_KEYS]
    flt = RedactSecretsFilter(secrets)
    for name in ("", "uvicorn", "uvicorn.error", "uvicorn.access", "case_manager"):
        logger = logging.getLogger(name)
        logger.addFilter(flt)
        for h in logger.handlers:
            h.addFilter(flt)
