"""REST API(v3: 書面・依頼者対応・継続性)。"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import hmac
import io
import json
import secrets
import urllib.parse
import uuid
from pathlib import Path
from typing import Literal, Optional

from fastapi import Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from . import calendar_feed, db, documents
from .api import (LAST_ACTIVITY_SQL, get_conn, load_case, masked_title, require_reauth, router, session,
                  settings_int, touch)
from .api_v2 import _run_row, finance_summary, worktime
from .main import audit

REFERRAL_SOURCES = ["紹介(弁護士)", "紹介(知人・依頼者)", "顧問先", "法テラス", "弁護士会の相談", "ウェブサイト・広告",
                    "既存の依頼者", "その他"]
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def download(data: bytes | str, filename: str, media_type: str) -> Response:
    q = urllib.parse.quote(filename)
    return Response(data, media_type=media_type, headers={
        "Content-Disposition": f"attachment; filename=\"download{Path(filename).suffix}\"; filename*=UTF-8''{q}"})


def safe_name(s: str) -> str:
    return "".join(c for c in s if c not in '\\/:*?"<>|').strip()[:60] or "document"


def templates_dir(request: Request) -> Path:
    d = request.app.state.settings.data_dir / "templates"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------- 事務所情報

class OfficeIn(BaseModel):
    事務所名: str = ""
    弁護士名: str = ""
    事務所住所: str = ""
    事務所電話: str = ""
    事務所FAX: str = ""
    所属弁護士会: str = ""
    登録番号: str = ""


@router.get("/settings/office")
def get_office(conn=Depends(get_conn)):
    return documents.office_info(conn)


@router.put("/settings/office")
def put_office(body: OfficeIn, conn=Depends(get_conn)):
    for label, key in documents.OFFICE_KEYS.items():
        db.set_setting(conn, key, getattr(body, label).strip())
    return {"ok": True}


@router.get("/meta/v3")
def meta_v3():
    return {"referral_sources": REFERRAL_SOURCES, "merge_fields": documents.FIELD_HELP}


# ---------------------------------------------------------------- 書面ひな形と差し込み

@router.get("/doc-templates")
def list_templates(conn=Depends(get_conn)):
    own = db.rows(conn.execute("SELECT id, name, note, created_at FROM doc_templates ORDER BY name"))
    for t in own:
        t["id"] = str(t["id"])
        t["builtin"] = False
    return documents.builtin_templates() + own


@router.post("/doc-templates", status_code=201)
def upload_template(request: Request, file: UploadFile = File(...), name: str = Form(""), note: str = Form(""),
                    conn=Depends(get_conn)):
    fn = Path(file.filename or "").name
    if Path(fn).suffix.lower() != ".docx":
        raise HTTPException(422, "Word(.docx)のひな形を選択してください")
    data = file.file.read(20 * 1024 * 1024 + 1)
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, "ファイルが大きすぎます")
    try:
        fields = documents.placeholders_in_docx(data)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(422, "Word ファイルとして読み込めません") from e
    stored = f"{uuid.uuid4().hex[:12]}.docx"
    (templates_dir(request) / stored).write_bytes(data)
    tid = conn.execute("INSERT INTO doc_templates(name, filename, note, created_at) VALUES(?,?,?,?)",
                       (name.strip() or Path(fn).stem, stored, note, db.now())).lastrowid
    unknown = [f for f in fields if f not in documents.FIELD_HELP]
    return {"id": tid, "fields": fields, "unknown_fields": unknown}


@router.delete("/doc-templates/{tid}")
def delete_template(tid: int, request: Request, conn=Depends(get_conn)):
    r = conn.execute("SELECT * FROM doc_templates WHERE id=?", (tid,)).fetchone()
    if not r:
        raise HTTPException(404, "見つかりません")
    (templates_dir(request) / r["filename"]).unlink(missing_ok=True)
    conn.execute("DELETE FROM doc_templates WHERE id=?", (tid,))
    return {"ok": True}


def _render(request: Request, conn, case_id: int, template: str) -> tuple[bytes, list[str], str]:
    fields = documents.merge_fields(conn, case_id)
    if template.startswith("builtin:"):
        stem = template.split(":", 1)[1]
        try:
            data, missing, _ = documents.render_builtin(stem, fields)
        except FileNotFoundError as e:
            raise HTTPException(404, "ひな形が見つかりません") from e
        return data, missing, stem.split("_", 1)[-1]
    if not template.isdigit():
        raise HTTPException(404, "ひな形が見つかりません")
    r = conn.execute("SELECT * FROM doc_templates WHERE id=?", (int(template),)).fetchone()
    if not r:
        raise HTTPException(404, "ひな形が見つかりません")
    data, missing = documents.fill_docx(templates_dir(request) / r["filename"], fields)
    return data, missing, r["name"]


@router.get("/cases/{case_id}/documents/check")
def check_document(case_id: int, template: str, request: Request, conn=Depends(get_conn)):
    """差し込みで空欄になる項目を事前に確認する。"""
    load_case(conn, case_id, session(request))
    _, missing, name = _render(request, conn, case_id, template)
    return {"name": name, "missing": missing}


@router.get("/cases/{case_id}/documents/render")
def render_document(case_id: int, template: str, request: Request, conn=Depends(get_conn)):
    c = load_case(conn, case_id, session(request))
    data, missing, name = _render(request, conn, case_id, template)
    audit(conn, request, "書面の作成", "template", None, case_id, {"template": name, "missing": missing})
    return download(data, f"{safe_name(name)}_{safe_name(c['title'])}.docx", DOCX_MIME)


# ---------------------------------------------------------------- 1ページ現状要約

def case_snapshot(conn, case_id: int, activities: int = 8) -> dict:
    c = dict(conn.execute(f"SELECT c.*, {LAST_ACTIVITY_SQL} AS last_activity FROM cases c WHERE c.id=?",
                          (case_id,)).fetchone())
    q = lambda sql, *a: db.rows(conn.execute(sql, (case_id, *a)))  # noqa: E731
    c["parties"] = q("SELECT * FROM parties WHERE case_id=? ORDER BY id")
    c["deadlines"] = q("SELECT * FROM deadlines WHERE case_id=? AND done=0 ORDER BY due_date, due_time")
    for d in c["deadlines"]:
        d.pop("calc_json", None)
    c["todos"] = q("SELECT * FROM todos WHERE case_id=? AND status!='完了' ORDER BY status='待ち' DESC, id")
    c["activities"] = q("SELECT * FROM activities WHERE case_id=? ORDER BY date DESC, id DESC LIMIT ?", activities)
    c["communications"] = q("""SELECT m.*, p.name AS party_name FROM communications m LEFT JOIN parties p
        ON p.id=m.party_id WHERE m.case_id=? ORDER BY m.date DESC, m.id DESC LIMIT 5""")
    c["checklist_open"] = [r["label"] for r in conn.execute(
        "SELECT label FROM checklist_items WHERE case_id=? AND done=0 ORDER BY sort, id", (case_id,))]
    c["finance"] = finance_summary(q("SELECT * FROM finance_entries WHERE case_id=?"))
    c["worktime_minutes"] = worktime(conn, case_id)["minutes"]
    last_status = conn.execute("SELECT id, result_json, created_at FROM ai_runs WHERE case_id=? AND kind='status' "
                               "AND status='完了' ORDER BY id DESC LIMIT 1", (case_id,)).fetchone()
    c["ai_status"] = None
    if last_status and last_status["result_json"]:
        res = json.loads(last_status["result_json"])
        c["ai_status"] = {"run_id": last_status["id"], "created_at": last_status["created_at"],
                          "headline": res.get("headline", "")}
    limit = c["stale_days"] or settings_int(conn, "stale_days", 30)
    idle = (db.today() - dt.date.fromisoformat(c["last_activity"][:10])).days
    c["idle_days"], c["stale"] = idle, c["status"] != "終結" and idle >= limit
    return c


@router.get("/cases/{case_id}/summary")
def case_summary(case_id: int, request: Request, conn=Depends(get_conn)):
    load_case(conn, case_id, session(request), request)
    return case_snapshot(conn, case_id)


# ---------------------------------------------------------------- AI 文書の Word 出力

@router.get("/ai/runs/{run_id}/docx")
def ai_run_docx(run_id: int, request: Request, conn=Depends(get_conn)):
    from .api_v2 import render_text

    d = _run_row(conn, run_id, session(request))
    if not d["result"]:
        raise HTTPException(400, "結果がありません")
    office = documents.office_info(conn)
    c = conn.execute("SELECT title FROM cases WHERE id=?", (d["case_id"],)).fetchone()
    if d["kind"] == "report":
        client = conn.execute("SELECT name FROM parties WHERE case_id=? AND role IN ('依頼者','相談者') ORDER BY id LIMIT 1",
                              (d["case_id"],)).fetchone()
        data = documents.letter_docx(client["name"] if client else "〔依頼者〕", d["result"]["subject"],
                                     [p["text"] for p in d["result"]["paragraphs"]], office)
        name = f"報告書(下書き)_{safe_name(c['title'])}.docx"
    else:
        data = documents.text_to_docx(render_text(d["kind"], d["result"], d["question"]))
        name = f"AI初稿_{d['kind']}_{safe_name(c['title'])}.docx"
    audit(conn, request, "AI文書の出力", "ai_run", run_id, d["case_id"])
    return download(data, name, DOCX_MIME)


# ---------------------------------------------------------------- カレンダー連携

def _cal_settings(conn) -> dict:
    return {"enabled": bool(db.get_setting(conn, "cal_token_hash")),
            "title_mode": db.get_setting(conn, "cal_title_mode", "full"),
            "include_todos": db.get_setting(conn, "cal_include_todos", "1") == "1",
            "last_access": db.get_setting(conn, "cal_last_access")}


class CalSettingsIn(BaseModel):
    title_mode: Literal["full", "masked"] = "full"
    include_todos: bool = True


@router.get("/calendar/settings")
def cal_settings(conn=Depends(get_conn)):
    return _cal_settings(conn)


@router.put("/calendar/settings")
def put_cal_settings(body: CalSettingsIn, conn=Depends(get_conn)):
    db.set_setting(conn, "cal_title_mode", body.title_mode)
    db.set_setting(conn, "cal_include_todos", "1" if body.include_todos else "0")
    return {"ok": True}


@router.post("/calendar/token")
def new_cal_token(request: Request, conn=Depends(get_conn)):
    """購読 URL を発行(再発行すると以前の URL は無効)。URL はこの応答でのみ表示する。"""
    require_reauth(session(request))
    token = secrets.token_urlsafe(32)
    db.set_setting(conn, "cal_token_hash", hashlib.sha256(token.encode()).hexdigest())
    audit(conn, request, "カレンダー購読URLの発行")
    return {"path": f"/cal/{token}.ics"}


@router.delete("/calendar/token")
def del_cal_token(request: Request, conn=Depends(get_conn)):
    db.set_setting(conn, "cal_token_hash", "")
    audit(conn, request, "カレンダー購読の停止")
    return {"ok": True}


def calendar_events(conn, title_mode: str, include_todos: bool, salt: str) -> list[list[str]]:
    since = (db.today() - dt.timedelta(days=60)).isoformat()
    evs = []
    for d in db.rows(conn.execute(
            """SELECT d.*, c.title AS case_title, c.sensitive FROM deadlines d JOIN cases c ON c.id=d.case_id
               WHERE d.done=0 AND d.due_date>=? ORDER BY d.due_date""", (since,))):
        desc = "" if (title_mode == "masked" or d["sensitive"]) else (d["note"] or "")
        if not d["confirmed"]:
            desc = "自動計算の期限です。アプリで根拠を確認して確定してください。\n" + desc
        evs.append(calendar_feed.event_lines(
            uid=calendar_feed.uid_for("deadline", d["id"], salt), summary=calendar_feed.deadline_summary(d, title_mode),
            date=d["due_date"], time=d["due_time"] or "", description=desc,
            location="" if d["sensitive"] else (d["place"] or "")))
    if include_todos:
        for t in db.rows(conn.execute(
                """SELECT t.*, c.title AS case_title, c.sensitive FROM todos t JOIN cases c ON c.id=t.case_id
                   WHERE t.status!='完了' AND t.due_date IS NOT NULL AND t.due_date>=?""", (since,))):
            case = f"案件#{t['case_id']}" if (title_mode == "masked" or t["sensitive"]) else t["case_title"]
            evs.append(calendar_feed.event_lines(
                uid=calendar_feed.uid_for("todo", t["id"], salt), summary=f"TODO: {t['title']}({case})",
                date=t["due_date"], alarms=("-PT15H",)))
    return evs


def calendar_route(app):
    """/cal/<token>.ics(Cookie 認証の外。トークンで照合)。"""

    @app.get("/cal/{token}.ics")
    def cal_feed(token: str, request: Request):
        conn = db.connect(request.app.state.settings.db_path)
        try:
            h = db.get_setting(conn, "cal_token_hash") or ""
            if not h or not hmac.compare_digest(h, hashlib.sha256(token.encode()).hexdigest()):
                raise HTTPException(404, "Not Found")
            st = _cal_settings(conn)
            last = st["last_access"]
            if not last or last[:10] != db.today().isoformat():
                audit(conn, request, "カレンダー購読の取得(当日初回)")
            db.set_setting(conn, "cal_last_access", db.now())
            body = calendar_feed.calendar("案件管理", calendar_events(conn, st["title_mode"], st["include_todos"], h[:16]))
        finally:
            conn.close()
        return Response(body, media_type="text/calendar; charset=utf-8", headers={"Cache-Control": "no-store"})


@router.get("/deadlines/{item_id}/ics")
def deadline_ics(item_id: int, request: Request, conn=Depends(get_conn)):
    r = conn.execute("""SELECT d.*, c.title AS case_title, c.sensitive FROM deadlines d JOIN cases c ON c.id=d.case_id
                        WHERE d.id=?""", (item_id,)).fetchone()
    if not r:
        raise HTTPException(404, "見つかりません")
    d = dict(r)
    load_case(conn, d["case_id"], session(request))
    ev = calendar_feed.event_lines(uid=calendar_feed.uid_for("deadline", d["id"], "single"),
                                   summary=calendar_feed.deadline_summary(d, "full"), date=d["due_date"],
                                   time=d["due_time"] or "", description=d["note"] or "", location=d["place"] or "")
    return download(calendar_feed.calendar("案件管理", [ev]), f"{safe_name(d['title'])}.ics", "text/calendar")


# ---------------------------------------------------------------- 保管期限

def retention_list(conn, sess) -> dict:
    years = settings_int(conn, "retention_years", 5)
    today = db.today()
    out = []
    for c in db.rows(conn.execute("SELECT id, title, field, status, sensitive, closed_on, retention_until, disposed_on, "
                                  "disposal_note FROM cases WHERE status='終結' ORDER BY closed_on")):
        until = c["retention_until"]
        if not until and c["closed_on"]:
            cd = dt.date.fromisoformat(c["closed_on"])
            try:
                until = cd.replace(year=cd.year + years).isoformat()
            except ValueError:   # 2/29
                until = cd.replace(year=cd.year + years, day=28).isoformat()
        state = "廃棄済み" if c["disposed_on"] else "終結日未入力" if not until else \
            "保管期限経過" if dt.date.fromisoformat(until) < today else "保管中"
        c.update(retention_until=until, state=state, title=masked_title(c, sess))
        out.append(c)
    return {"years": years, "cases": out, "due": [c for c in out if c["state"] == "保管期限経過"]}


@router.get("/retention")
def get_retention(request: Request, conn=Depends(get_conn)):
    return retention_list(conn, session(request))


class RetentionIn(BaseModel):
    retention_until: Optional[dt.date] = None
    disposed_on: Optional[dt.date] = None
    disposal_note: Optional[str] = Field(default=None, max_length=500)


@router.put("/cases/{case_id}/retention")
def put_retention(case_id: int, body: RetentionIn, request: Request, conn=Depends(get_conn)):
    """保管期限の個別設定・廃棄の記録(記録の削除は行わない。廃棄は紙・電子記録を別途処理する)。"""
    sess = session(request)
    c = load_case(conn, case_id, sess)
    data = body.model_dump(exclude_unset=True)
    if "disposed_on" in data:
        require_reauth(sess)
        if c["status"] != "終結":
            raise HTTPException(422, "終結した案件のみ廃棄を記録できます")
    data = {k: (v.isoformat() if isinstance(v, dt.date) else v) for k, v in data.items()}
    if data:
        conn.execute(f"UPDATE cases SET {','.join(k + '=?' for k in data)} WHERE id=?", (*data.values(), case_id))
        audit(conn, request, "保管期限・廃棄の記録", "case", case_id, case_id, data)
    return {"ok": True}


class RetentionYearsIn(BaseModel):
    years: int = Field(ge=1, le=100)


@router.put("/settings/retention")
def put_retention_years(body: RetentionYearsIn, conn=Depends(get_conn)):
    db.set_setting(conn, "retention_years", str(body.years))
    return {"ok": True}


# ---------------------------------------------------------------- 引継ぎ書出し

class HandoverIn(BaseModel):
    case_ids: Optional[list[int]] = None
    statuses: list[Literal["相談", "受任", "係属", "終結"]] = ["受任", "係属"]
    include_sensitive: bool = False
    format: Literal["docx", "csv"] = "docx"
    note: str = Field(default="", max_length=2000)


@router.post("/export/handover")
def export_handover(body: HandoverIn, request: Request, conn=Depends(get_conn)):
    """第三者の弁護士に渡す案件一覧。再認証必須・監査ログに記録。"""
    require_reauth(session(request))
    if body.case_ids:
        ids = [r["id"] for r in conn.execute(
            f"SELECT id FROM cases WHERE id IN ({','.join('?' * len(body.case_ids))}) ORDER BY id", body.case_ids)]
    else:
        ids = [r["id"] for r in conn.execute(
            f"SELECT id FROM cases WHERE status IN ({','.join('?' * len(body.statuses))}) ORDER BY "
            "CASE status WHEN '係属' THEN 0 WHEN '受任' THEN 1 ELSE 2 END, id", body.statuses)]
    snaps = [case_snapshot(conn, i, activities=10) for i in ids]
    if not body.include_sensitive:
        snaps = [s for s in snaps if not s["sensitive"]]
    if not snaps:
        raise HTTPException(422, "対象の案件がありません")
    audit(conn, request, "引継ぎ書の出力", detail={"format": body.format, "case_ids": [s["id"] for s in snaps]})
    stamp = db.today().strftime("%Y%m%d")
    if body.format == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["No.", "事件名", "分野", "状態", "受任日", "裁判所", "事件番号", "依頼者", "相手方", "次の期限・期日",
                    "期限の内容", "待ち・TODO", "未収報酬", "預り金残高", "記録フォルダ", "メモ"])
        for i, s in enumerate(snaps, 1):
            nd = s["deadlines"][0] if s["deadlines"] else None
            w.writerow([i, s["title"], s["field"], s["status"], s["accepted_on"] or "", s["court"], s["case_number"],
                        "、".join(p["name"] for p in s["parties"] if p["role"] in ("依頼者", "相談者")),
                        "、".join(p["name"] for p in s["parties"] if p["role"] == "相手方"),
                        nd["due_date"] if nd else "", nd["title"] if nd else "",
                        " / ".join(t["title"] + (f"({t['waiting_for']})" if t["waiting_for"] else "") for t in s["todos"]),
                        s["finance"]["fees"]["receivable"], s["finance"]["deposit"]["balance"], s["folder_path"],
                        s["memo"]])
        return download("﻿" + buf.getvalue(), f"引継ぎ案件一覧_{stamp}.csv", "text/csv; charset=utf-8")
    data = documents.handover_docx(snaps, documents.office_info(conn), body.note)
    return download(data, f"事件引継書_{stamp}.docx", DOCX_MIME)


# ---------------------------------------------------------------- 受任経路・分野別の集計

@router.get("/reports/analysis")
def analysis(request: Request, date_from: Optional[str] = Query(None), date_to: Optional[str] = Query(None),
             conn=Depends(get_conn)):
    """受任日(なければ登録日)が期間内の案件を、分野別・受任経路別に集計。報酬は入金ベース(実費・預り金除く)。"""
    where, args = [], []
    base = "COALESCE(c.accepted_on, substr(c.created_at,1,10))"
    if date_from:
        where.append(f"{base}>=?")
        args.append(date_from)
    if date_to:
        where.append(f"{base}<=?")
        args.append(date_to)
    cases = db.rows(conn.execute(
        "SELECT c.id, c.field, c.status, COALESCE(NULLIF(c.referral_source,''),'未設定') AS source FROM cases c"
        + (" WHERE " + " AND ".join(where) if where else ""), args))

    def agg(key: str) -> list[dict]:
        groups: dict[str, dict] = {}
        for c in cases:
            g = groups.setdefault(c[key], {"key": c[key], "cases": 0, "consultations": 0, "active": 0, "closed": 0,
                                           "fees_received": 0, "minutes": 0})
            g["cases"] += 1
            g[{"相談": "consultations", "終結": "closed"}.get(c["status"], "active")] += 1
            rows = db.rows(conn.execute("SELECT * FROM finance_entries WHERE case_id=?", (c["id"],)))
            g["fees_received"] += finance_summary(rows)["fees"]["received"]
            g["minutes"] += worktime(conn, c["id"])["minutes"]
        for g in groups.values():
            g["hourly"] = round(g["fees_received"] / (g["minutes"] / 60)) if g["minutes"] else None
            g["avg_fee"] = round(g["fees_received"] / g["cases"]) if g["cases"] else 0
        return sorted(groups.values(), key=lambda g: -g["fees_received"])

    return {"by_field": agg("field"), "by_source": agg("source"), "total_cases": len(cases)}
