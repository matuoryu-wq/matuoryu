"""案件フォルダの索引化と、案件内に限定した本文検索。"""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

from . import db
from .extract import SUPPORTED, ExtractError, extract

CHUNK_CHARS = 900


def iter_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith((".", "~$")))
        for fn in sorted(filenames):
            if fn.startswith((".", "~$")):
                continue
            p = Path(dirpath) / fn
            if p.suffix.lower() in SUPPORTED:
                yield p


def split_chunks(text: str, size: int = CHUNK_CHARS) -> list[str]:
    """段落・文の境界でおおむね size 文字ずつに分ける。"""
    if len(text) <= size:
        return [text] if text else []
    pieces = re.split(r"(?<=[。.!?!?\n])", text)
    out, buf = [], ""
    for p in pieces:
        if len(buf) + len(p) > size and buf:
            out.append(buf.strip())
            buf = ""
        while len(p) > size:      # 句点のない長文
            out.append(p[:size])
            p = p[size:]
        buf += p
    if buf.strip():
        out.append(buf.strip())
    return out


def index_case(conn, case_id: int, root: Path, ocr_lang: str = "jpn", progress=None) -> dict:
    """差分索引化。変更のないファイルは再抽出しない。"""
    existing = {r["rel_path"]: dict(r) for r in conn.execute(
        "SELECT * FROM doc_files WHERE case_id=?", (case_id,))}
    files = list(iter_files(root))
    seen, stats = set(), {"total": len(files), "indexed": 0, "unchanged": 0, "errors": 0, "removed": 0, "empty": 0}
    for i, path in enumerate(files, 1):
        rel = path.relative_to(root).as_posix()
        seen.add(rel)
        st = path.stat()
        old = existing.get(rel)
        if old and old["mtime"] == st.st_mtime and old["size"] == st.st_size and old["status"] in ("ok", "empty"):
            stats["unchanged"] += 1
            continue
        if progress:
            progress(f"{i}/{len(files)} {rel}")
        try:
            ex = extract(path, ocr_lang)
            status = "ok" if any(p.text for p in ex.parts) else "empty"
            message, method, pages = ex.message, ex.method, ex.pages
        except ExtractError as e:
            ex, status, message, method, pages = None, "error", str(e), "", 0
        except Exception as e:  # noqa: BLE001  壊れたファイル等
            ex, status, message, method, pages = None, "error", f"{type(e).__name__}: {e}", "", 0
        conn.execute("BEGIN")
        try:
            if old:
                conn.execute("DELETE FROM doc_chunks WHERE file_id=?", (old["id"],))
                conn.execute("UPDATE doc_files SET mtime=?, size=?, status=?, method=?, pages=?, message=?, "
                             "indexed_at=? WHERE id=?",
                             (st.st_mtime, st.st_size, status, method, pages, message, db.now(), old["id"]))
                fid = old["id"]
            else:
                fid = conn.execute(
                    "INSERT INTO doc_files(case_id, rel_path, mtime, size, status, method, pages, message, indexed_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?)",
                    (case_id, rel, st.st_mtime, st.st_size, status, method, pages, message, db.now())).lastrowid
            if ex:
                for part in ex.parts:
                    for chunk in split_chunks(part.text):
                        conn.execute(
                            "INSERT INTO doc_chunks(case_id, source_type, file_id, rel_path, page, loc, text) "
                            "VALUES(?,?,?,?,?,?,?)", (case_id, "file", fid, rel, part.page, part.loc, chunk))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        stats["indexed" if status == "ok" else "empty" if status == "empty" else "errors"] += 1
    for rel, old in existing.items():
        if rel not in seen:
            conn.execute("DELETE FROM doc_files WHERE id=?", (old["id"],))
            stats["removed"] += 1
    return stats


def fmt_time(sec: float) -> str:
    sec = int(sec or 0)
    return f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def add_transcript_chunks(conn, case_id: int, transcript_id: int, filename: str, segments: list[dict],
                          speakers: dict | None = None) -> None:
    """文字起こしを約60秒ごとの塊にして検索・出典の対象にする。"""
    speakers = speakers or {}
    conn.execute("DELETE FROM doc_chunks WHERE transcript_id=?", (transcript_id,))
    buf: list[dict] = []

    def flush():
        if not buf:
            return
        lines = [f"[{fmt_time(s['start'])} {speakers.get(s.get('speaker') or '', s.get('speaker') or '話者不明')}] {s['text']}"
                 for s in buf]
        t0, t1 = buf[0]["start"], buf[-1]["end"]
        conn.execute(
            "INSERT INTO doc_chunks(case_id, source_type, transcript_id, rel_path, t_start, t_end, loc, text) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (case_id, "audio", transcript_id, f"録音:{filename}", t0, t1,
             f"{fmt_time(t0)}〜{fmt_time(t1)}", "\n".join(lines)))
        buf.clear()

    for s in segments:
        if buf and (s["start"] - buf[0]["start"] > 60 or sum(len(x["text"]) for x in buf) > CHUNK_CHARS):
            flush()
        buf.append(s)
    flush()


def search(conn, case_id: int, q: str, limit: int = 50) -> list[dict]:
    """案件内の資料・録音を検索(他案件は対象外)。"""
    terms = [t for t in re.split(r"\s+", unicodedata.normalize("NFKC", q).strip()) if t]
    if not terms:
        return []
    long_terms = [t for t in terms if len(t) >= 3]
    short_terms = [t for t in terms if len(t) < 3]
    sql = "SELECT c.* FROM doc_chunks c"
    args: list = []
    where = ["c.case_id=?"]
    args.append(case_id)
    if long_terms:
        sql += " JOIN doc_fts f ON f.rowid=c.id"
        where.append("doc_fts MATCH ?")
        args.append(" AND ".join('"' + t.replace('"', '""') + '"' for t in long_terms))
    for t in short_terms:
        where.append("c.text LIKE ? ESCAPE '\\'")
        args.append("%" + t.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
    sql += " WHERE " + " AND ".join(where) + " ORDER BY c.source_type, c.rel_path, c.page, c.t_start LIMIT ?"
    args.append(limit)
    out = []
    for r in db.rows(conn.execute(sql, args)):
        r["snippet"] = _snippet(r["text"], terms)
        out.append(r)
    return out


def _snippet(text: str, terms: list[str], width: int = 120) -> str:
    flat = " ".join(text.split())
    pos = min((flat.find(t) for t in terms if t in flat), default=0)
    start = max(0, pos - 40)
    return ("…" if start else "") + flat[start:start + width] + ("…" if start + width < len(flat) else "")
