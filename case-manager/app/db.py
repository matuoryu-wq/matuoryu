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

-- ---------------------------------------------------------------- v2
CREATE TABLE IF NOT EXISTS anon_terms (
    id INTEGER PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    term TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '固有名',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS doc_files (
    id INTEGER PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    rel_path TEXT NOT NULL,
    mtime REAL,
    size INTEGER,
    status TEXT NOT NULL,          -- ok / empty / error / skipped
    method TEXT DEFAULT '',        -- text / ocr / mixed
    pages INTEGER DEFAULT 0,
    message TEXT DEFAULT '',
    indexed_at TEXT NOT NULL,
    UNIQUE(case_id, rel_path)
);

CREATE TABLE IF NOT EXISTS doc_chunks (
    id INTEGER PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,     -- file / audio
    file_id INTEGER REFERENCES doc_files(id) ON DELETE CASCADE,
    transcript_id INTEGER REFERENCES transcripts(id) ON DELETE CASCADE,
    rel_path TEXT NOT NULL,
    page INTEGER,
    t_start REAL,
    t_end REAL,
    loc TEXT NOT NULL,             -- 表示用の位置(p.3 / 段落5〜9 / 00:01:23〜)
    text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_case ON doc_chunks(case_id);

CREATE VIRTUAL TABLE IF NOT EXISTS doc_fts USING fts5(
    text, content='doc_chunks', content_rowid='id', tokenize='trigram'
);
CREATE TRIGGER IF NOT EXISTS doc_chunks_ai AFTER INSERT ON doc_chunks BEGIN
    INSERT INTO doc_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER IF NOT EXISTS doc_chunks_ad AFTER DELETE ON doc_chunks BEGIN
    INSERT INTO doc_fts(doc_fts, rowid, text) VALUES ('delete', old.id, old.text);
END;

CREATE TABLE IF NOT EXISTS transcripts (
    id INTEGER PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    recorded_on TEXT,
    duration REAL,
    status TEXT NOT NULL DEFAULT '待機',   -- 待機 / 処理中 / 完了 / 失敗
    message TEXT DEFAULT '',
    engine TEXT DEFAULT '',
    segments_json TEXT,
    speakers_json TEXT,
    activity_id INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_runs (
    id INTEGER PRIMARY KEY,
    case_id INTEGER REFERENCES cases(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,             -- ask / memo / timeline
    question TEXT DEFAULT '',
    status TEXT NOT NULL,           -- 送信前停止 / 完了 / 失敗
    model TEXT DEFAULT '',
    prompt_version TEXT DEFAULT '',
    sent_text TEXT DEFAULT '',      -- 実際に送信した内容(匿名化済み)
    response_text TEXT DEFAULT '',  -- 受信した内容(匿名化済み)
    mapping_json TEXT DEFAULT '',   -- 置換表(PC内のみ。送信しない)
    sources_json TEXT DEFAULT '',
    result_json TEXT DEFAULT '',    -- 復元・出典照合済みの結果
    input_tokens INTEGER,
    output_tokens INTEGER,
    error TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    case_id INTEGER,
    status TEXT NOT NULL,           -- 待機 / 処理中 / 完了 / 失敗
    progress TEXT DEFAULT '',
    result_id INTEGER,
    error TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS finance_entries (
    id INTEGER PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('請求','入金','実費支出','預り金受入','預り金支出','預り金返還')),
    category TEXT NOT NULL DEFAULT 'その他',
    amount INTEGER NOT NULL CHECK (amount >= 0),
    note TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_finance_case ON finance_entries(case_id, date);

-- ---------------------------------------------------------------- v3
CREATE TABLE IF NOT EXISTS doc_templates (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    filename TEXT NOT NULL,          -- data/templates 内のファイル名
    note TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
"""

# 既存DBへの列追加(CREATE TABLE IF NOT EXISTS では反映されないもの)
MIGRATIONS = [
    ("activities", "transcript_id", "INTEGER"),
    # v3
    ("cases", "referral_source", "TEXT DEFAULT ''"),   # 受任経路
    ("cases", "retention_until", "TEXT"),             # 保管期限(個別指定。空なら終結日+既定年数)
    ("cases", "disposed_on", "TEXT"),                 # 記録の廃棄日
    ("cases", "disposal_note", "TEXT DEFAULT ''"),    # 廃棄方法等
]


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
    for table, col, typ in MIGRATIONS:
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if col not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")


def rows(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    r = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT INTO settings(key,value) VALUES(?,?) "
                 "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
