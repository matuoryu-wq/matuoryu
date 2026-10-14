"""REST API(v1: 案件管理の中核)。"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

from . import backup, conflicts, db, deadlines, templates
from .main import COOKIE, SessionInfo, audit, check_token, new_session

router = APIRouter(prefix="/api")

STATUSES = ["相談", "受任", "係属", "終結"]
ROLES = ["依頼者", "相手方", "相手方代理人", "関係者", "相談者"]
ACTIVITY_KINDS = ["面談", "電話", "書面提出", "書面受領", "期日", "調査", "打合せ", "その他"]
CHANNELS = ["電話", "メール", "面談", "郵送", "FAX", "チャット", "その他"]
ADVERSE_ROLES = {"相手方", "相手方代理人"}


# ---------------------------------------------------------------- 共通

def get_conn(request: Request):
    conn = db.connect(request.app.state.settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


def session(request: Request) -> SessionInfo:
    return request.state.session


def require_reauth(sess: SessionInfo) -> None:
    if not sess.reauth_ok:
        raise HTTPException(403, detail={"code": "reauth_required", "message": "再認証が必要です"})


def load_case(conn, case_id: int, sess: SessionInfo, request: Request | None = None) -> dict:
    r = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    if not r:
        raise HTTPException(404, "案件が見つかりません")
    c = dict(r)
    if c["sensitive"]:
        require_reauth(sess)
        if request is not None and request.method == "GET":
            audit(conn, request, "機微案件の閲覧", "case", case_id, case_id)
    return c


def case_of(conn, table: str, item_id: int) -> int:
    r = conn.execute(f"SELECT case_id FROM {table} WHERE id=?", (item_id,)).fetchone()
    if not r:
        raise HTTPException(404, "対象が見つかりません")
    return r["case_id"]


def touch(conn, case_id: int) -> None:
    conn.execute("UPDATE cases SET updated_at=? WHERE id=?", (db.now(), case_id))


def insert(conn, table: str, data: dict) -> int:
    cols = ",".join(data)
    qs = ",".join("?" for _ in data)
    return conn.execute(f"INSERT INTO {table}({cols}) VALUES({qs})", tuple(data.values())).lastrowid


def update(conn, table: str, item_id: int, data: dict) -> None:
    if not data:
        return
    sets = ",".join(f"{k}=?" for k in data)
    conn.execute(f"UPDATE {table} SET {sets} WHERE id=?", (*data.values(), item_id))


def dump(model: BaseModel, partial: bool = False) -> dict:
    d = model.model_dump(exclude_unset=partial)
    return {k: (v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v) for k, v in d.items()}


def masked_title(row: dict, sess: SessionInfo) -> str:
    if row.get("sensitive") and not sess.reauth_ok:
        return f"🔒 機微案件 #{row.get('case_id') or row.get('id')}"
    return row.get("case_title") or row.get("title")


def settings_int(conn, key: str, default: int) -> int:
    try:
        return int(db.get_setting(conn, key, str(default)))
    except (TypeError, ValueError):
        return default


def custom_holidays(conn) -> dict[dt.date, str]:
    return {dt.date.fromisoformat(r["date"]): r["name"] for r in conn.execute("SELECT * FROM custom_holidays")}


def check_folder(request: Request, folder: str) -> str:
    folder = (folder or "").strip().strip('"')
    if not folder:
        return ""
    p = Path(folder)
    if not p.is_absolute():
        raise HTTPException(422, "フォルダは絶対パスで指定してください")
    roots = request.app.state.settings.allowed_folder_roots
    if roots and not any(_within(p, r) for r in roots):
        raise HTTPException(422, "許可されていない場所のフォルダです(ALLOWED_FOLDER_ROOTS)")
    return folder


def _within(p: Path, root: Path) -> bool:
    try:
        p.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


# ---------------------------------------------------------------- 認証

class TokenIn(BaseModel):
    token: str


@router.post("/auth/login")
def login(body: TokenIn, request: Request, conn=Depends(get_conn)):
    lim = request.app.state.limiter
    if lim.blocked():
        audit(conn, request, "ログイン拒否(試行回数超過)")
        raise HTTPException(429, "試行回数が多すぎます。10分後に再試行してください")
    if not check_token(request.app.state.settings, body.token):
        lim.fail()
        audit(conn, request, "ログイン失敗")
        raise HTTPException(401, "トークンが正しくありません")
    lim.reset()
    sid = new_session(conn, request)
    audit(conn, request, "ログイン")
    resp = JSONResponse({"ok": True})
    secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    resp.set_cookie(COOKIE, sid, httponly=True, samesite="strict", secure=secure,
                    max_age=request.app.state.settings.session_hours * 3600)
    return resp


@router.post("/auth/logout")
def logout(request: Request, conn=Depends(get_conn)):
    sess = session(request)
    if sess.id_hash:
        conn.execute("DELETE FROM sessions WHERE id_hash=?", (sess.id_hash,))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE)
    return resp


@router.post("/auth/reauth")
def reauth(body: TokenIn, request: Request, conn=Depends(get_conn)):
    sess = session(request)
    lim = request.app.state.limiter
    if lim.blocked():
        raise HTTPException(429, "試行回数が多すぎます")
    if not check_token(request.app.state.settings, body.token):
        lim.fail()
        audit(conn, request, "再認証失敗")
        raise HTTPException(401, "トークンが正しくありません")
    lim.reset()
    if sess.id_hash:
        conn.execute("UPDATE sessions SET reauth_at=? WHERE id_hash=?", (db.now(), sess.id_hash))
    audit(conn, request, "再認証")
    return {"ok": True, "minutes": sess.reauth_minutes}


@router.get("/auth/status")
def auth_status(request: Request):
    sess = session(request)
    return {"authenticated": True, "reauth_ok": sess.reauth_ok, "reauth_minutes": sess.reauth_minutes}


# ---------------------------------------------------------------- メタ情報

@router.get("/meta")
def meta():
    return {
        "statuses": STATUSES,
        "fields": templates.FIELDS,
        "roles": ROLES,
        "activity_kinds": ACTIVITY_KINDS,
        "channels": CHANNELS,
        "rulesets": {k: {"name": v.name, "holiday_rule": v.holiday_rule} for k, v in deadlines.RULESETS.items()},
        "presets": [p.__dict__ for p in deadlines.PRESETS],
        "units": deadlines.UNIT_LABEL,
    }


# ---------------------------------------------------------------- 案件

class CaseIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    field: str = "その他"
    status: Literal["相談", "受任", "係属", "終結"] = "相談"
    accepted_on: Optional[dt.date] = None
    closed_on: Optional[dt.date] = None
    court: str = ""
    case_number: str = ""
    fee_terms: str = ""
    memo: str = ""
    sensitive: bool = False
    folder_path: str = ""
    stale_days: Optional[int] = Field(default=None, ge=1, le=3650)


class CaseCreate(CaseIn):
    with_checklist: bool = True


class CasePatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    field: Optional[str] = None
    status: Optional[Literal["相談", "受任", "係属", "終結"]] = None
    accepted_on: Optional[dt.date] = None
    closed_on: Optional[dt.date] = None
    court: Optional[str] = None
    case_number: Optional[str] = None
    fee_terms: Optional[str] = None
    memo: Optional[str] = None
    sensitive: Optional[bool] = None
    folder_path: Optional[str] = None
    stale_days: Optional[int] = Field(default=None, ge=1, le=3650)


LAST_ACTIVITY_SQL = """
    MAX(c.updated_at,
        COALESCE((SELECT MAX(a.date) FROM activities a WHERE a.case_id=c.id), ''),
        COALESCE((SELECT MAX(m.date) FROM communications m WHERE m.case_id=c.id), ''))
"""


@router.get("/cases")
def list_cases(request: Request, status: Optional[str] = None, field: Optional[str] = None,
               conn=Depends(get_conn)):
    sess = session(request)
    sql = f"""SELECT c.*, {LAST_ACTIVITY_SQL} AS last_activity,
        (SELECT MIN(d.due_date) FROM deadlines d WHERE d.case_id=c.id AND d.done=0) AS next_due,
        (SELECT GROUP_CONCAT(p.name, '、') FROM parties p WHERE p.case_id=c.id AND p.role='依頼者') AS clients
        FROM cases c WHERE 1=1"""
    args: list = []
    if status:
        sql += " AND c.status IN (%s)" % ",".join("?" for _ in status.split(","))
        args += status.split(",")
    if field:
        sql += " AND c.field=?"
        args.append(field)
    sql += " ORDER BY CASE c.status WHEN '係属' THEN 0 WHEN '受任' THEN 1 WHEN '相談' THEN 2 ELSE 3 END, c.updated_at DESC"
    out = []
    for r in db.rows(conn.execute(sql, args)):
        if r["sensitive"] and not sess.reauth_ok:
            r = {"id": r["id"], "title": masked_title(r, sess), "sensitive": 1, "status": r["status"],
                 "field": r["field"], "next_due": r["next_due"], "last_activity": r["last_activity"],
                 "masked": True}
        out.append(r)
    return out


@router.post("/cases", status_code=201)
def create_case(body: CaseCreate, request: Request, conn=Depends(get_conn)):
    data = dump(body)
    with_cl = data.pop("with_checklist")
    data["folder_path"] = check_folder(request, data["folder_path"])
    data["sensitive"] = int(data["sensitive"])
    data["created_at"] = data["updated_at"] = db.now()
    conn.execute("BEGIN")
    try:
        cid = insert(conn, "cases", data)
        if with_cl:
            for i, label in enumerate(templates.checklist_for(body.field)):
                insert(conn, "checklist_items", {"case_id": cid, "label": label, "sort": i})
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return {"id": cid}


@router.get("/cases/{case_id}")
def get_case(case_id: int, request: Request, conn=Depends(get_conn)):
    sess = session(request)
    c = load_case(conn, case_id, sess, request)
    q = lambda sql: db.rows(conn.execute(sql, (case_id,)))  # noqa: E731
    c["parties"] = q("SELECT * FROM parties WHERE case_id=? ORDER BY CASE role WHEN '依頼者' THEN 0 WHEN '相談者' THEN 1 WHEN '相手方' THEN 2 ELSE 3 END, id")
    c["deadlines"] = q("SELECT * FROM deadlines WHERE case_id=? ORDER BY done, due_date, due_time")
    for d in c["deadlines"]:
        d["calc"] = json.loads(d.pop("calc_json")) if d.get("calc_json") else None
    c["checklist"] = q("SELECT * FROM checklist_items WHERE case_id=? ORDER BY sort, id")
    c["activities"] = q("SELECT * FROM activities WHERE case_id=? ORDER BY date DESC, id DESC")
    c["communications"] = q("""SELECT m.*, p.name AS party_name, p.role AS party_role FROM communications m
        LEFT JOIN parties p ON p.id=m.party_id WHERE m.case_id=? ORDER BY m.date DESC, m.id DESC""")
    c["todos"] = q("SELECT * FROM todos WHERE case_id=? ORDER BY status='完了', COALESCE(due_date,'9999'), id")
    c["last_activity"] = conn.execute(f"SELECT {LAST_ACTIVITY_SQL} AS v FROM cases c WHERE c.id=?",
                                      (case_id,)).fetchone()["v"]
    return c


@router.put("/cases/{case_id}")
def update_case(case_id: int, body: CasePatch, request: Request, conn=Depends(get_conn)):
    sess = session(request)
    cur = load_case(conn, case_id, sess)
    data = dump(body, partial=True)
    if "folder_path" in data:
        data["folder_path"] = check_folder(request, data["folder_path"] or "")
    if "sensitive" in data:
        data["sensitive"] = int(bool(data["sensitive"]))
        if cur["sensitive"] and not data["sensitive"]:
            require_reauth(sess)
    if data.get("status") == "終結" and not cur["closed_on"] and "closed_on" not in data:
        data["closed_on"] = db.today().isoformat()
    data["updated_at"] = db.now()
    update(conn, "cases", case_id, data)
    return {"ok": True}


@router.delete("/cases/{case_id}")
def delete_case(case_id: int, request: Request, conn=Depends(get_conn)):
    sess = session(request)
    require_reauth(sess)
    c = load_case(conn, case_id, sess)
    conn.execute("DELETE FROM cases WHERE id=?", (case_id,))
    audit(conn, request, "案件削除", "case", case_id, case_id, {"title": c["title"]})
    return {"ok": True}


# ---------------------------------------------------------------- 子要素の汎用 CRUD

def child_routes(table: str, path: str, create_model, patch_model, prepare=None):
    def create(case_id: int, body, request: Request, conn=Depends(get_conn)):
        load_case(conn, case_id, session(request))
        data = dump(body)
        if prepare:
            data = prepare(conn, case_id, data, create=True)
        data["case_id"] = case_id
        if table not in ("checklist_items",):
            data.setdefault("created_at", db.now())
        if table == "todos":
            data["updated_at"] = data["created_at"]
        item_id = insert(conn, table, data)
        touch(conn, case_id)
        return {"id": item_id}

    def patch(item_id: int, body, request: Request, conn=Depends(get_conn)):
        case_id = case_of(conn, table, item_id)
        load_case(conn, case_id, session(request))
        data = dump(body, partial=True)
        if prepare:
            data = prepare(conn, case_id, data, create=False, item_id=item_id)
        update(conn, table, item_id, data)
        touch(conn, case_id)
        return {"ok": True}

    def delete(item_id: int, request: Request, conn=Depends(get_conn)):
        case_id = case_of(conn, table, item_id)
        load_case(conn, case_id, session(request))
        conn.execute(f"DELETE FROM {table} WHERE id=?", (item_id,))
        touch(conn, case_id)
        return {"ok": True}

    # from __future__ annotations により型が文字列化されるため、実際のモデルを設定する
    create.__annotations__.update(body=create_model, request=Request)
    patch.__annotations__.update(body=patch_model, request=Request)
    delete.__annotations__.update(request=Request)
    for fn in (create, patch, delete):
        fn.__annotations__.update({k: int for k in ("case_id", "item_id") if k in fn.__annotations__})
    router.add_api_route(f"/cases/{{case_id}}/{path}", create, methods=["POST"], status_code=201)
    router.add_api_route(f"/{path}/{{item_id}}", patch, methods=["PUT"])
    router.add_api_route(f"/{path}/{{item_id}}", delete, methods=["DELETE"])


# 当事者
class PartyIn(BaseModel):
    role: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=200)
    kana: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    note: str = ""


class PartyPatch(BaseModel):
    role: Optional[str] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    kana: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    note: Optional[str] = None


child_routes("parties", "parties", PartyIn, PartyPatch)


# 期限・期日
class DeadlineIn(BaseModel):
    kind: Literal["期限", "期日"] = "期限"
    title: str = Field(min_length=1)
    due_date: dt.date
    due_time: str = ""
    place: str = ""
    note: str = ""
    calc: Optional[dict] = None   # 自動計算の結果(根拠・過程)


class DeadlinePatch(BaseModel):
    kind: Optional[Literal["期限", "期日"]] = None
    title: Optional[str] = None
    due_date: Optional[dt.date] = None
    due_time: Optional[str] = None
    place: Optional[str] = None
    note: Optional[str] = None
    done: Optional[bool] = None


def _prep_deadline(conn, case_id, data, create, item_id=None):
    if create:
        calc = data.pop("calc", None)
        if calc:
            # 自動計算の期限は未確認として登録し、人間の承認を待つ
            data["calc_json"] = json.dumps(calc, ensure_ascii=False)
            data["confirmed"] = 0
        else:
            data["confirmed"] = 1
            data["confirmed_at"] = db.now()
    else:
        if "done" in data:
            data["done"] = int(bool(data["done"]))
        if "due_date" in data:
            r = conn.execute("SELECT calc_json, due_date, note FROM deadlines WHERE id=?", (item_id,)).fetchone()
            if r["calc_json"] and r["due_date"] != data["due_date"]:
                base = data["note"] if data.get("note") is not None else (r["note"] or "")
                data["note"] = base + f"(計算値 {r['due_date']} から手動変更)"
    return data


child_routes("deadlines", "deadlines", DeadlineIn, DeadlinePatch, _prep_deadline)


@router.post("/deadlines/{item_id}/confirm")
def confirm_deadline(item_id: int, request: Request, conn=Depends(get_conn)):
    case_id = case_of(conn, "deadlines", item_id)
    load_case(conn, case_id, session(request))
    conn.execute("UPDATE deadlines SET confirmed=1, confirmed_at=? WHERE id=?", (db.now(), item_id))
    audit(conn, request, "期限の確定(承認)", "deadline", item_id, case_id)
    return {"ok": True}


@router.get("/deadlines")
def list_deadlines(request: Request, days: int = 60, include_done: bool = False, include_past: bool = True,
                   conn=Depends(get_conn)):
    sess = session(request)
    until = (db.today() + dt.timedelta(days=days)).isoformat()
    sql = """SELECT d.*, c.title AS case_title, c.sensitive, c.status AS case_status FROM deadlines d
             JOIN cases c ON c.id=d.case_id WHERE d.due_date<=?"""
    args: list = [until]
    if not include_done:
        sql += " AND d.done=0"
    if not include_past:
        sql += " AND d.due_date>=?"
        args.append(db.today().isoformat())
    sql += " ORDER BY d.due_date, d.due_time"
    out = db.rows(conn.execute(sql, args))
    for d in out:
        d["case_title"] = masked_title(d, sess)
        d.pop("calc_json", None)
    return out


# 期限計算
class CalcIn(BaseModel):
    event_date: dt.date
    preset: Optional[str] = None
    amount: Optional[int] = Field(default=None, ge=1, le=1200)
    unit: Optional[Literal["day", "week", "month", "year"]] = None
    ruleset: Literal["minso", "keiso", "minpo"] = "minso"
    include_first_day: bool = False
    extend_on_holiday: bool = True


@router.post("/deadline-calc")
def deadline_calc(body: CalcIn, conn=Depends(get_conn)):
    extra = custom_holidays(conn)
    if body.preset:
        if body.preset not in deadlines.PRESETS_BY_CODE:
            raise HTTPException(422, "不明なプリセットです")
        p, res = deadlines.compute_preset(body.preset, body.event_date, extra)
        out = res.to_dict()
        out["title"] = p.name
        out["preset"] = p.code
        return out
    if not body.amount or not body.unit:
        raise HTTPException(422, "期間と単位を指定してください")
    res = deadlines.compute_deadline(body.event_date, body.amount, body.unit, body.ruleset,
                                     body.include_first_day, body.extend_on_holiday, extra)
    out = res.to_dict()
    out["title"] = f"{body.amount}{deadlines.UNIT_LABEL[body.unit]}の期間"
    return out


# チェックリスト
class ChecklistIn(BaseModel):
    label: str = Field(min_length=1)
    sort: int = 999


class ChecklistPatch(BaseModel):
    label: Optional[str] = None
    done: Optional[bool] = None


def _prep_check(conn, case_id, data, create, item_id=None):
    if "done" in data:
        data["done"] = int(bool(data["done"]))
        data["done_at"] = db.now() if data["done"] else None
    return data


child_routes("checklist_items", "checklist", ChecklistIn, ChecklistPatch, _prep_check)


# 活動記録
class ActivityIn(BaseModel):
    date: dt.date
    kind: str = "その他"
    content: str = Field(min_length=1)
    minutes: Optional[int] = Field(default=None, ge=0, le=24 * 60)


class ActivityPatch(BaseModel):
    date: Optional[dt.date] = None
    kind: Optional[str] = None
    content: Optional[str] = None
    minutes: Optional[int] = Field(default=None, ge=0, le=24 * 60)


child_routes("activities", "activities", ActivityIn, ActivityPatch)


# 連絡履歴
class CommIn(BaseModel):
    party_id: Optional[int] = None
    date: dt.date
    channel: str = "電話"
    direction: Literal["発信", "受信"] = "発信"
    summary: str = Field(min_length=1)


class CommPatch(BaseModel):
    party_id: Optional[int] = None
    date: Optional[dt.date] = None
    channel: Optional[str] = None
    direction: Optional[Literal["発信", "受信"]] = None
    summary: Optional[str] = None


def _prep_comm(conn, case_id, data, create, item_id=None):
    pid = data.get("party_id")
    if pid is not None:
        r = conn.execute("SELECT case_id FROM parties WHERE id=?", (pid,)).fetchone()
        if not r or r["case_id"] != case_id:
            raise HTTPException(422, "当事者がこの案件に属していません")
    return data


child_routes("communications", "communications", CommIn, CommPatch, _prep_comm)


# TODO・待ち状態
class TodoIn(BaseModel):
    title: str = Field(min_length=1)
    status: Literal["未着手", "待ち", "完了"] = "未着手"
    waiting_for: str = ""
    due_date: Optional[dt.date] = None


class TodoPatch(BaseModel):
    title: Optional[str] = None
    status: Optional[Literal["未着手", "待ち", "完了"]] = None
    waiting_for: Optional[str] = None
    due_date: Optional[dt.date] = None


def _prep_todo(conn, case_id, data, create, item_id=None):
    if not create:
        data["updated_at"] = db.now()
    if data.get("status") == "完了":
        data["done_at"] = db.now()
    elif "status" in data:
        data["done_at"] = None
    return data


child_routes("todos", "todos", TodoIn, TodoPatch, _prep_todo)


@router.get("/todos")
def list_todos(request: Request, status: str = "未着手,待ち", conn=Depends(get_conn)):
    sess = session(request)
    sts = status.split(",")
    sql = f"""SELECT t.*, c.title AS case_title, c.sensitive FROM todos t JOIN cases c ON c.id=t.case_id
              WHERE t.status IN ({",".join("?" for _ in sts)})
              ORDER BY t.status='待ち', COALESCE(t.due_date,'9999'), t.updated_at"""
    out = db.rows(conn.execute(sql, sts))
    for t in out:
        t["case_title"] = masked_title(t, sess)
        t["waiting_days"] = (db.today() - dt.date.fromisoformat(t["updated_at"][:10])).days
    return out


# ---------------------------------------------------------------- 放置案件

def stale_cases(conn, sess: SessionInfo) -> list[dict]:
    default = settings_int(conn, "stale_days", 30)
    sql = f"""SELECT c.id, c.title, c.status, c.field, c.sensitive, c.stale_days,
        {LAST_ACTIVITY_SQL} AS last_activity,
        (SELECT GROUP_CONCAT(t.title || '(' || t.waiting_for || ')', ' / ') FROM todos t
            WHERE t.case_id=c.id AND t.status='待ち') AS waiting
        FROM cases c WHERE c.status != '終結'"""
    out = []
    for r in db.rows(conn.execute(sql)):
        limit = r["stale_days"] or default
        last = dt.date.fromisoformat(r["last_activity"][:10])
        idle = (db.today() - last).days
        if idle >= limit:
            r["idle_days"], r["limit_days"] = idle, limit
            r["title"] = masked_title(r, sess)
            out.append(r)
    return sorted(out, key=lambda x: -x["idle_days"])


@router.get("/stale")
def get_stale(request: Request, conn=Depends(get_conn)):
    return stale_cases(conn, session(request))


# ---------------------------------------------------------------- 利益相反

class NameIn(BaseModel):
    name: str = Field(min_length=1)
    kana: str = ""


class ConflictIn(BaseModel):
    names: list[NameIn] = Field(min_length=1, max_length=50)
    exclude_case_id: Optional[int] = None
    role_of_names: str = "相談者・相手方"


@router.post("/conflicts/check")
def conflict_check(body: ConflictIn, request: Request, conn=Depends(get_conn)):
    sess = session(request)
    parties = db.rows(conn.execute(
        """SELECT p.id, p.name, p.kana, p.role, p.case_id, c.title AS case_title, c.status, c.sensitive
           FROM parties p JOIN cases c ON c.id=p.case_id"""))
    results = []
    for n in body.names:
        hits = []
        for p in parties:
            if body.exclude_case_id and p["case_id"] == body.exclude_case_id:
                continue
            score, why = conflicts.match_score(n.name, n.kana, p["name"], p["kana"] or "")
            if score >= conflicts.THRESHOLD:
                hits.append({
                    "party_id": p["id"], "party_name": p["name"], "party_kana": p["kana"], "role": p["role"],
                    "case_id": p["case_id"], "case_title": masked_title(p, sess), "case_status": p["status"],
                    "score": round(score, 2), "reason": why,
                    "level": "一致" if score >= 0.95 else "類似",
                    "adverse": p["role"] in ADVERSE_ROLES,
                })
        hits.sort(key=lambda h: (-h["score"], not h["adverse"]))
        results.append({"name": n.name, "kana": n.kana, "normalized": conflicts.normalize_name(n.name), "hits": hits})
    total = sum(len(r["hits"]) for r in results)
    check_id = insert(conn, "conflict_checks", {
        "checked_at": db.now(), "names": "、".join(n.name for n in body.names),
        "result_json": json.dumps(results, ensure_ascii=False), "hit_count": total})
    audit(conn, request, "利益相反チェック", "conflict_check", check_id,
          detail={"names": len(body.names), "hits": total})
    return {"id": check_id, "results": results, "hit_count": total,
            "note": "表記ゆれを吸収して照合しています。過剰検出を優先しているため、該当の有無は記録を確認して判断してください。"}


class ConclusionIn(BaseModel):
    conclusion: str


@router.put("/conflicts/{check_id}")
def conflict_conclude(check_id: int, body: ConclusionIn, conn=Depends(get_conn)):
    conn.execute("UPDATE conflict_checks SET conclusion=? WHERE id=?", (body.conclusion, check_id))
    return {"ok": True}


@router.get("/conflicts/history")
def conflict_history(limit: int = 50, conn=Depends(get_conn)):
    return db.rows(conn.execute(
        "SELECT id, checked_at, names, hit_count, conclusion FROM conflict_checks ORDER BY id DESC LIMIT ?", (limit,)))


# ---------------------------------------------------------------- 資料(フォルダ)

MAX_FILES = 3000


def _case_folder(conn, case_id: int, sess: SessionInfo, request: Request) -> Path:
    c = load_case(conn, case_id, sess)
    if not c["folder_path"]:
        raise HTTPException(404, "フォルダが紐付けられていません")
    root = Path(c["folder_path"])
    check_folder(request, str(root))
    if not root.is_dir():
        raise HTTPException(404, f"フォルダが見つかりません: {root}")
    return root


@router.get("/cases/{case_id}/files")
def list_files(case_id: int, request: Request, conn=Depends(get_conn)):
    root = _case_folder(conn, case_id, session(request), request)
    notes = {r["rel_path"]: r["note"] for r in conn.execute(
        "SELECT rel_path, note FROM document_notes WHERE case_id=?", (case_id,))}
    files, truncated = [], False
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith((".", "~$")))
        for fn in sorted(filenames):
            if fn.startswith((".", "~$")) or fn.lower() in ("thumbs.db", "desktop.ini"):
                continue
            full = Path(dirpath) / fn
            try:
                st = full.stat()
            except OSError:
                continue
            rel = full.relative_to(root).as_posix()
            files.append({"path": rel, "size": st.st_size,
                          "mtime": dt.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="minutes"),
                          "note": notes.get(rel, "")})
            if len(files) >= MAX_FILES:
                truncated = True
                break
        if truncated:
            break
    return {"folder": str(root), "files": files, "truncated": truncated}


class FileNoteIn(BaseModel):
    path: str
    note: str


@router.put("/cases/{case_id}/files/note")
def file_note(case_id: int, body: FileNoteIn, request: Request, conn=Depends(get_conn)):
    load_case(conn, case_id, session(request))
    conn.execute("""INSERT INTO document_notes(case_id, rel_path, note, updated_at) VALUES(?,?,?,?)
        ON CONFLICT(case_id, rel_path) DO UPDATE SET note=excluded.note, updated_at=excluded.updated_at""",
                 (case_id, body.path, body.note, db.now()))
    touch(conn, case_id)
    return {"ok": True}


@router.get("/cases/{case_id}/files/open")
def open_file(case_id: int, path: str, request: Request, conn=Depends(get_conn)):
    root = _case_folder(conn, case_id, session(request), request)
    target = (root / path).resolve()
    if not _within(target, root) or not target.is_file():
        raise HTTPException(404, "ファイルが見つかりません")
    audit(conn, request, "資料の閲覧", "file", None, case_id, {"path": path})
    return FileResponse(target, filename=target.name, content_disposition_type="inline")


# ---------------------------------------------------------------- 横断検索

@router.get("/search")
def search(request: Request, q: str = Query(min_length=1, max_length=100), conn=Depends(get_conn)):
    sess = session(request)
    terms = [t for t in q.replace(" ", " ").split() if t]
    norm_terms = [conflicts.normalize_name(t) for t in terms]

    def like_all(cols: list[str]) -> tuple[str, list]:
        parts, args = [], []
        for t in terms:
            esc = t.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            parts.append("(" + " OR ".join(f"{c} LIKE ? ESCAPE '\\'" for c in cols) + ")")
            args += [f"%{esc}%"] * len(cols)
        return " AND ".join(parts), args

    results = []

    def add(kind, rows, text_key, case_key="case_id"):
        for r in rows:
            masked = r.get("sensitive") and not sess.reauth_ok
            results.append({
                "kind": kind, "case_id": r[case_key], "case_title": masked_title(r, sess),
                "id": r["id"], "date": r.get("date") or r.get("due_date") or "",
                "snippet": "" if masked else _snippet(r[text_key] or "", terms),
                "masked": bool(masked),
            })

    w, a = like_all(["c.title", "c.memo", "c.court", "c.case_number", "c.fee_terms"])
    add("案件", db.rows(conn.execute(
        f"SELECT c.id, c.id AS case_id, c.title, c.sensitive, c.title || ' ' || c.case_number || ' ' || c.memo AS text "
        f"FROM cases c WHERE {w} LIMIT 50", a)), "text")

    # 当事者は表記ゆれも考慮(正規化キーでも照合)
    rows = db.rows(conn.execute(
        "SELECT p.*, c.title AS case_title, c.sensitive FROM parties p JOIN cases c ON c.id=p.case_id"))
    hits = []
    for p in rows:
        blob = " ".join([p["name"], p["kana"] or "", p["phone"] or "", p["email"] or "", p["address"] or "", p["note"] or ""])
        nblob = conflicts.normalize_name(p["name"]) + " " + conflicts.normalize_name(p["kana"] or "")
        if all(t in blob or (nt and nt in nblob) for t, nt in zip(terms, norm_terms)):
            p["text"] = f"{p['role']}: {p['name']} {p['kana'] or ''} {p['phone'] or ''} {p['email'] or ''}"
            hits.append(p)
    add("当事者", hits[:50], "text")

    for kind, table, cols, text in [
        ("活動記録", "activities", ["x.content", "x.kind"], "content"),
        ("連絡履歴", "communications", ["x.summary", "x.channel"], "summary"),
        ("TODO", "todos", ["x.title", "x.waiting_for"], "title"),
        ("期限", "deadlines", ["x.title", "x.note", "x.place"], "title"),
    ]:
        w, a = like_all(cols)
        add(kind, db.rows(conn.execute(
            f"SELECT x.*, c.title AS case_title, c.sensitive FROM {table} x JOIN cases c ON c.id=x.case_id "
            f"WHERE {w} ORDER BY x.id DESC LIMIT 50", a)), text)

    w, a = like_all(["x.note", "x.rel_path"])
    add("資料メモ", db.rows(conn.execute(
        f"SELECT x.*, x.rel_path || ': ' || x.note AS text, c.title AS case_title, c.sensitive "
        f"FROM document_notes x JOIN cases c ON c.id=x.case_id WHERE {w} LIMIT 50", a)), "text")
    return {"q": q, "results": results}


def _snippet(text: str, terms: list[str], width: int = 60) -> str:
    text = " ".join(text.split())
    pos = min((text.find(t) for t in terms if t in text), default=0)
    start = max(0, pos - width // 3)
    s = text[start:start + width]
    return ("…" if start > 0 else "") + s + ("…" if start + width < len(text) else "")


# ---------------------------------------------------------------- ダッシュボード・通知

def _notifications(conn, sess: SessionInfo) -> list[dict]:
    notify_days = settings_int(conn, "notify_days", 7)
    today = db.today()
    out = []
    for d in db.rows(conn.execute(
            """SELECT d.*, c.title AS case_title, c.sensitive FROM deadlines d JOIN cases c ON c.id=d.case_id
               WHERE d.done=0 AND d.due_date<=? ORDER BY d.due_date""",
            ((today + dt.timedelta(days=notify_days)).isoformat(),))):
        left = (dt.date.fromisoformat(d["due_date"]) - today).days
        level = "danger" if left <= 1 else "warning" if left <= 3 else "info"
        when = "期限超過" if left < 0 else "本日" if left == 0 else f"あと{left}日"
        out.append({"level": level, "type": "deadline", "case_id": d["case_id"], "id": d["id"],
                    "text": f"【{when}】{d['kind']} {d['title']}({masked_title(d, sess)})",
                    "due_date": d["due_date"], "unconfirmed": not d["confirmed"]})
    for d in db.rows(conn.execute(
            "SELECT d.*, c.title AS case_title, c.sensitive FROM deadlines d JOIN cases c ON c.id=d.case_id "
            "WHERE d.done=0 AND d.confirmed=0")):
        out.append({"level": "warning", "type": "unconfirmed", "case_id": d["case_id"], "id": d["id"],
                    "text": f"未確定の計算期限: {d['title']} {d['due_date']}({masked_title(d, sess)})"})
    for s in stale_cases(conn, sess):
        out.append({"level": "info", "type": "stale", "case_id": s["id"],
                    "text": f"{s['idle_days']}日間動きなし: {s['title']}"})
    last = db.get_setting(conn, "last_backup_at")
    if not last or (dt.datetime.now() - dt.datetime.fromisoformat(last)) > dt.timedelta(hours=48):
        out.append({"level": "warning", "type": "backup", "text": "48時間以上バックアップされていません"})
    err = db.get_setting(conn, "last_backup_error")
    if err:
        out.append({"level": "danger", "type": "backup", "text": f"バックアップ失敗: {err}"})
    return out


@router.get("/notifications")
def notifications(request: Request, conn=Depends(get_conn)):
    return _notifications(conn, session(request))


@router.get("/dashboard")
def dashboard(request: Request, conn=Depends(get_conn)):
    sess = session(request)
    today = db.today()
    upcoming = list_deadlines(request, days=14, include_done=False, include_past=True, conn=conn)
    for d in upcoming:
        d["days_left"] = (dt.date.fromisoformat(d["due_date"]) - today).days
    active = [c for c in list_cases(request, status="受任,係属", conn=conn)]
    counts = {r["status"]: r["n"] for r in conn.execute("SELECT status, COUNT(*) n FROM cases GROUP BY status")}
    return {
        "today": today.isoformat(),
        "upcoming": upcoming,
        "active_cases": active,
        "todos": list_todos(request, status="未着手,待ち", conn=conn),
        "stale": stale_cases(conn, sess),
        "counts": counts,
        "last_backup_at": db.get_setting(conn, "last_backup_at"),
        "last_backup_error": db.get_setting(conn, "last_backup_error"),
        "backup_configured": request.app.state.settings.backup_dir is not None,
        "notifications": _notifications(conn, sess),
        "reauth_ok": sess.reauth_ok,
    }


# ---------------------------------------------------------------- 設定・休日・バックアップ・監査

class SettingsIn(BaseModel):
    stale_days: Optional[int] = Field(default=None, ge=1, le=3650)
    notify_days: Optional[int] = Field(default=None, ge=0, le=365)


@router.get("/settings")
def get_settings(request: Request, conn=Depends(get_conn)):
    s = request.app.state.settings
    return {
        "stale_days": settings_int(conn, "stale_days", 30),
        "notify_days": settings_int(conn, "notify_days", 7),
        "backup_dir": str(s.backup_dir) if s.backup_dir else "",
        "backup_keep": s.backup_keep,
        "allowed_folder_roots": [str(r) for r in s.allowed_folder_roots],
        "reauth_minutes": s.reauth_minutes,
        "last_backup_at": db.get_setting(conn, "last_backup_at"),
        "last_backup_file": db.get_setting(conn, "last_backup_file"),
        "last_backup_error": db.get_setting(conn, "last_backup_error"),
    }


@router.put("/settings")
def put_settings(body: SettingsIn, conn=Depends(get_conn)):
    for k, v in body.model_dump(exclude_none=True).items():
        db.set_setting(conn, k, str(v))
    return {"ok": True}


class HolidayIn(BaseModel):
    date: dt.date
    name: str = Field(min_length=1)


@router.get("/holidays")
def get_holidays(year: int = Query(default_factory=lambda: db.today().year), conn=Depends(get_conn)):
    from .holidays_jp import holidays_of_year
    return {
        "national": [{"date": d.isoformat(), "name": n} for d, n in holidays_of_year(year).items()],
        "custom": db.rows(conn.execute("SELECT * FROM custom_holidays ORDER BY date")),
    }


@router.post("/holidays", status_code=201)
def add_holiday(body: HolidayIn, conn=Depends(get_conn)):
    conn.execute("INSERT OR REPLACE INTO custom_holidays(date,name) VALUES(?,?)", (body.date.isoformat(), body.name))
    return {"ok": True}


@router.delete("/holidays/{date}")
def del_holiday(date: str, conn=Depends(get_conn)):
    conn.execute("DELETE FROM custom_holidays WHERE date=?", (date,))
    return {"ok": True}


@router.post("/backup/run")
def backup_now(request: Request):
    s = request.app.state.settings
    if not s.backup_dir:
        raise HTTPException(400, "BACKUP_DIR が設定されていません(.env)")
    try:
        dest = backup.run_backup(s.db_path, s.backup_dir, s.backup_keep)
    except Exception as e:  # noqa: BLE001
        backup.record_failure(s.db_path, e)
        raise HTTPException(500, f"バックアップに失敗しました: {e}") from e
    return {"ok": True, "file": dest.name}


@router.get("/audit")
def audit_log(request: Request, limit: int = Query(200, le=1000), offset: int = 0, conn=Depends(get_conn)):
    require_reauth(session(request))
    return db.rows(conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)))


@router.get("/checklist-templates")
def checklist_templates():
    return {f: templates.checklist_for(f) for f in templates.FIELDS}


@router.post("/cases/{case_id}/checklist/apply-template")
def apply_template(case_id: int, request: Request, conn=Depends(get_conn)):
    c = load_case(conn, case_id, session(request))
    existing = {r["label"] for r in conn.execute("SELECT label FROM checklist_items WHERE case_id=?", (case_id,))}
    added = 0
    for i, label in enumerate(templates.checklist_for(c["field"])):
        if label not in existing:
            insert(conn, "checklist_items", {"case_id": case_id, "label": label, "sort": i})
            added += 1
    return {"added": added}
