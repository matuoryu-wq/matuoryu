"""日次バックアップ(別ドライブ)。SQLite のオンラインバックアップ API を使う。"""
from __future__ import annotations

import datetime as dt
import logging
import sqlite3
import threading
from pathlib import Path

from . import db

log = logging.getLogger("case_manager")


def run_backup(db_path: Path, backup_dir: Path, keep: int = 30) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = backup_dir / f"cases-{stamp}.sqlite3"
    src = sqlite3.connect(db_path)
    try:
        out = sqlite3.connect(dest)
        with out:
            src.backup(out)
        out.close()
    finally:
        src.close()
    # 検証: 開けて整合性チェックが通ること
    chk = sqlite3.connect(dest)
    try:
        ok = chk.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        chk.close()
    if ok != "ok":
        raise RuntimeError(f"バックアップの整合性チェックに失敗: {ok}")
    olds = sorted(backup_dir.glob("cases-*.sqlite3"))
    for old in olds[: max(0, len(olds) - keep)]:
        old.unlink(missing_ok=True)
    conn = db.connect(db_path)
    try:
        db.set_setting(conn, "last_backup_at", db.now())
        db.set_setting(conn, "last_backup_file", dest.name)
        db.set_setting(conn, "last_backup_error", "")
    finally:
        conn.close()
    return dest


def record_failure(db_path: Path, err: Exception) -> None:
    conn = db.connect(db_path)
    try:
        db.set_setting(conn, "last_backup_error", f"{db.now()} {type(err).__name__}: {err}")
    finally:
        conn.close()


def _due(db_path: Path) -> bool:
    conn = db.connect(db_path)
    try:
        last = db.get_setting(conn, "last_backup_at")
    finally:
        conn.close()
    if not last:
        return True
    return dt.datetime.now() - dt.datetime.fromisoformat(last) >= dt.timedelta(hours=24)


def start_scheduler(db_path: Path, backup_dir: Path | None, keep: int) -> threading.Event | None:
    """サーバー稼働中、1時間ごとに確認し24時間経過していればバックアップする。"""
    if not backup_dir:
        log.warning("BACKUP_DIR 未設定のため自動バックアップは無効です")
        return None
    stop = threading.Event()

    def loop() -> None:
        while not stop.is_set():
            try:
                if _due(db_path):
                    dest = run_backup(db_path, backup_dir, keep)
                    log.info("バックアップ完了: %s", dest)
            except Exception as e:  # noqa: BLE001
                log.error("バックアップ失敗: %s", e)
                record_failure(db_path, e)
            stop.wait(3600)

    threading.Thread(target=loop, name="backup", daemon=True).start()
    return stop
