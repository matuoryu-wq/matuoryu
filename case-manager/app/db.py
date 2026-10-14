"""SQLite スキーマと接続。"""
from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    field TEXT NOT NULL DEFAULT 'その他',
    status TEXT NOT NULL DEFAULT '相談' CHECK (status IN ('相談','受任','係属','終結')),
    accepted_on TEXT,
    closed_on TEXT,
    court TEXT DEFAULT '',
    case_number TEXT DEFAULT '',
    fee_terms TEXT DEFAULT '',
    memo TEXT DEFAULT '',
    sensitive INTEGER NOT NULL DEFAULT 0,
    folder_path TEXT DEFAULT '',
    stale_days INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS parties (
    id INTEGER PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    name TEXT NOT NULL,
    kana TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    email TEXT DEFAULT '',
    address TEXT DEFAULT '',
    note TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_parties_case ON parties(case_id);

CREATE TABLE IF NOT EXISTS deadlines (
    id INTEGER PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    kind TEXT NOT NULL DEFAULT '期限' CHECK (kind IN ('期限','期日')),
    title TEXT NOT NULL,
    due_date TEXT NOT NULL,
    due_time TEXT DEFAULT '',
    place TEXT DEFAULT '',
    note TEXT DEFAULT '',
    done INTEGER NOT NULL DEFAULT 0,
    confirmed INTEGER NOT NULL DEFAULT 1,
    confirmed_at TEXT,
    calc_json TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_deadlines_due ON deadlines(due_date);

CREATE TABLE IF NOT EXISTS checklist_items (
    id INTEGER PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0,
    done_at TEXT,
    sort INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    minutes INTEGER,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_activities_case ON activities(case_id, date);

CREATE TABLE IF NOT EXISTS communications (
    id INTEGER PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    party_id INTEGER REFERENCES parties(id) ON DELETE SET NULL,
    date TEXT NOT NULL,
    channel TEXT NOT NULL,
    direction TEXT NOT NULL DEFAULT '発信',
    summary TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_comm_case ON communications(case_id, date);

CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT '未着手' CHECK (status IN ('未着手','待ち','完了')),
    waiting_for TEXT DEFAULT '',
    due_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    done_at TEXT
);

CREATE TABLE IF NOT EXISTS document_notes (
    id INTEGER PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    rel_path TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL,
    UNIQUE(case_id, rel_path)
);

CREATE TABLE IF NOT EXISTS conflict_checks (
    id INTEGER PRIMARY KEY,
    checked_at TEXT NOT NULL,
    names TEXT NOT NULL,
    result_json TEXT NOT NULL,
    hit_count INTEGER NOT NULL,
    conclusion TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS custom_holidays (
    date TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id_hash TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    reauth_at TEXT,
    user_agent TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,
    session TEXT DEFAULT '',
    ip TEXT DEFAULT '',
    action TEXT NOT NULL,
    entity TEXT DEFAULT '',
    entity_id INTEGER,
    case_id INTEGER,
    detail TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts);
"""


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def today() -> dt.date:
    return dt.date.today()


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def rows(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    r = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT INTO settings(key,value) VALUES(?,?) "
                 "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
