"""時間のかかる処理(索引化・文字起こし・AI生成)をバックグラウンドで1件ずつ実行する。"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from . import db

log = logging.getLogger("case_manager")
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="job")


def create(conn, kind: str, case_id: int | None) -> int:
    t = db.now()
    return conn.execute("INSERT INTO jobs(kind, case_id, status, created_at, updated_at) VALUES(?,?,?,?,?)",
                        (kind, case_id, "待機", t, t)).lastrowid


def update(db_path, job_id: int, **fields) -> None:
    conn = db.connect(db_path)
    try:
        fields["updated_at"] = db.now()
        sets = ",".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE jobs SET {sets} WHERE id=?", (*fields.values(), job_id))
    finally:
        conn.close()


def submit(db_path, job_id: int, fn, *, sync: bool = False) -> None:
    """fn(conn, progress) を実行し、戻り値を result_id として保存する。"""

    def run():
        update(db_path, job_id, status="処理中")
        conn = db.connect(db_path)
        try:
            result = fn(conn, lambda msg: update(db_path, job_id, progress=str(msg)[:200]))
            update(db_path, job_id, status="完了", result_id=result if isinstance(result, int) else None)
        except Exception as e:  # noqa: BLE001
            log.exception("ジョブ %s 失敗", job_id)
            update(db_path, job_id, status="失敗", error=f"{e}"[:500])
        finally:
            conn.close()

    if sync:
        run()
    else:
        _executor.submit(run)
