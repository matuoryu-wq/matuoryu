"""REST API(v2: AI・文字起こし・フォルダ索引・稼働/報酬/採算)。"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import re
import uuid
from pathlib import Path
from typing import Literal, Optional

from fastapi import Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from . import ai, db, indexer, jobs, llm
from .anonymize import AnonymizationLeak
from .api import (_case_folder, child_routes, get_conn, load_case, masked_title, require_reauth, router,
                  session, touch)
from .main import audit
from .transcribe import get_transcriber

AUDIO_EXT = {".m4a", ".mp3", ".wav", ".aac", ".mp4", ".caf", ".ogg", ".webm", ".flac", ".amr", ".3gp"}
MAX_AUDIO_BYTES = 1024 * 1024 * 1024
FEE_CATEGORIES = ["着手金", "報酬金", "日当", "タイムチャージ", "顧問料", "相談料", "その他報酬"]
EXPENSE_CATEGORIES = ["印紙", "郵券", "交通費", "謄写・記録取寄せ", "鑑定・調査", "その他実費"]


def _settings(request: Request):
    return request.app.state.settings


def _submit(request: Request, job_id: int, fn) -> None:
    s = _settings(request)
    jobs.submit(s.db_path, job_id, fn, sync=s.jobs_sync)


# ---------------------------------------------------------------- 状態

@router.get("/ai/status")
def ai_status(request: Request):
    s = _settings(request)
    from .extract import _ocr_available
    return {
        "ai_configured": bool(s.anthropic_api_key or s.llm_factory),
        "model": s.ai_model,
        "effort": s.ai_effort,
        "transcriber_installed": bool(s.transcriber_factory) or importlib.util.find_spec("faster_whisper") is not None,
        "whisper_model": s.whisper_model,
        "diarization": s.diarization,
        "ocr_available": _ocr_available(),
    }


@router.get("/jobs/{job_id}")
def get_job(job_id: int, conn=Depends(get_conn)):
    r = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not r:
        raise HTTPException(404, "ジョブが見つかりません")
    return dict(r)


# ---------------------------------------------------------------- 匿名化の追加語

class AnonTermIn(BaseModel):
    term: str = Field(min_length=2, max_length=100)
    category: str = "固有名"


@router.get("/cases/{case_id}/anon-terms")
def list_anon_terms(case_id: int, request: Request, conn=Depends(get_conn)):
    load_case(conn, case_id, session(request))
    return db.rows(conn.execute("SELECT * FROM anon_terms WHERE case_id=? ORDER BY id", (case_id,)))


@router.post("/cases/{case_id}/anon-terms", status_code=201)
def add_anon_term(case_id: int, body: AnonTermIn, request: Request, conn=Depends(get_conn)):
    load_case(conn, case_id, session(request))
    rid = conn.execute("INSERT INTO anon_terms(case_id, term, category, created_at) VALUES(?,?,?,?)",
                       (case_id, body.term.strip(), body.category.strip() or "固有名", db.now())).lastrowid
    return {"id": rid}


@router.delete("/anon-terms/{term_id}")
def del_anon_term(term_id: int, request: Request, conn=Depends(get_conn)):
    r = conn.execute("SELECT case_id FROM anon_terms WHERE id=?", (term_id,)).fetchone()
    if not r:
        raise HTTPException(404, "見つかりません")
    load_case(conn, r["case_id"], session(request))
    conn.execute("DELETE FROM anon_terms WHERE id=?", (term_id,))
    return {"ok": True}


# ---------------------------------------------------------------- AI

class AIIn(BaseModel):
    kind: Literal["ask", "memo", "timeline", "status", "report"]
    question: str = Field(default="", max_length=2000)


@router.post("/cases/{case_id}/ai/preview")
def ai_preview(case_id: int, body: AIIn, request: Request, conn=Depends(get_conn)):
    """送信内容(匿名化後)の確認。外部には何も送らない。"""
    load_case(conn, case_id, session(request))
    if body.kind == "ask" and not body.question.strip():
        raise HTTPException(422, "質問を入力してください")
    p = ai.prepare(conn, case_id, body.kind, body.question)
    return {
        "sent_text": p["user_anon"],
        "chars": len(p["user_anon"]),
        "sources": len(p["sources"]),
        "omitted_sources": p["omitted"],
        "replacements": p["anonymizer"].summary(),
        "leaks": p["leaks"],
        "prompt_version": p["version"],
    }


@router.post("/cases/{case_id}/ai/run", status_code=202)
def ai_run(case_id: int, body: AIIn, request: Request, conn=Depends(get_conn)):
    load_case(conn, case_id, session(request))
    s = _settings(request)
    client = llm.get_client(s)
    if client is None:
        raise HTTPException(400, "AI が未設定です(.env の ANTHROPIC_API_KEY)")
    if body.kind == "ask" and not body.question.strip():
        raise HTTPException(422, "質問を入力してください")
    job_id = jobs.create(conn, f"ai:{body.kind}", case_id)
    audit(conn, request, "AI実行を依頼", "job", job_id, case_id, {"kind": body.kind})

    def work(c, progress):
        progress("匿名化・送信中")
        try:
            return ai.run(c, None, client, case_id, body.kind, body.question)
        except AnonymizationLeak as e:
            raise RuntimeError(f"{e}: {'、'.join(e.leaks)}(案件の「AI」タブで追加の匿名化語を登録してください)") from e

    _submit(request, job_id, work)
    return {"job_id": job_id}


def _run_row(conn, run_id: int, sess) -> dict:
    r = conn.execute("SELECT * FROM ai_runs WHERE id=?", (run_id,)).fetchone()
    if not r:
        raise HTTPException(404, "見つかりません")
    load_case(conn, r["case_id"], sess)
    d = dict(r)
    d.pop("mapping_json", None)
    d["result"] = json.loads(d.pop("result_json")) if d.get("result_json") else None
    d.pop("sources_json", None)
    return d


@router.get("/ai/runs/{run_id}")
def get_ai_run(run_id: int, request: Request, conn=Depends(get_conn)):
    return _run_row(conn, run_id, session(request))


@router.get("/cases/{case_id}/ai/runs")
def list_ai_runs(case_id: int, request: Request, conn=Depends(get_conn)):
    load_case(conn, case_id, session(request))
    return db.rows(conn.execute(
        "SELECT id, kind, question, status, model, error, created_at, input_tokens, output_tokens "
        "FROM ai_runs WHERE case_id=? ORDER BY id DESC LIMIT 100", (case_id,)))


@router.get("/ai/log")
def ai_log(request: Request, limit: int = Query(200, le=1000), conn=Depends(get_conn)):
    """AI 送信ログ(全案件)。送信本文は匿名化済みのもの。"""
    require_reauth(session(request))
    return db.rows(conn.execute(
        """SELECT r.id, r.case_id, r.kind, r.status, r.model, r.prompt_version, r.error, r.created_at,
                  r.input_tokens, r.output_tokens, LENGTH(r.sent_text) AS sent_chars
           FROM ai_runs r ORDER BY r.id DESC LIMIT ?""", (limit,)))


@router.get("/ai/runs/{run_id}/csv")
def ai_run_csv(run_id: int, request: Request, conn=Depends(get_conn)):
    d = _run_row(conn, run_id, session(request))
    if d["kind"] != "timeline" or not d["result"]:
        raise HTTPException(400, "時系列・争点整理表のみ出力できます")
    return Response(ai.to_csv(d["result"]), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename=timeline-{run_id}.csv"})


@router.post("/ai/runs/{run_id}/save-activity", status_code=201)
def ai_save_activity(run_id: int, request: Request, conn=Depends(get_conn)):
    """AI 初稿(相談メモ等)を活動記録に保存する。"""
    d = _run_row(conn, run_id, session(request))
    if not d["result"]:
        raise HTTPException(400, "結果がありません")
    text = render_text(d["kind"], d["result"], d["question"])
    aid = conn.execute("INSERT INTO activities(case_id, date, kind, content, created_at) VALUES(?,?,?,?,?)",
                       (d["case_id"], db.today().isoformat(), "その他", text, db.now())).lastrowid
    touch(conn, d["case_id"])
    return {"id": aid}


def render_text(kind: str, result: dict, question: str = "") -> str:
    def cite(it):
        labels = [c.get("label") or c.get("source_id") for c in it.get("citations", [])]
        return f"〔{'; '.join(dict.fromkeys(labels))}〕" if labels else "〔出典なし〕"

    if kind == "memo":
        lines = ["【相談メモ(AI初稿・要確認)】"]
        for s in result["sections"]:
            lines.append(f"■ {s['heading']}")
            lines += [f"・{it['text']} {cite(it)}" for it in s["items"]] or ["・なし"]
        return "\n".join(lines)
    if kind == "ask":
        lines = [f"【AIへの質問(初稿・要確認)】{question}"]
        lines += [f"{it['text']} {cite(it)}" for it in result["answer"]]
        return "\n".join(lines)
    if kind == "status":
        lines = ["【現状要約(AI初稿・要確認)】", result["headline"]]
        for key, head in (("current_status", "現状"), ("next_steps", "次にすべきこと"), ("risks", "注意点")):
            lines.append(f"■ {head}")
            lines += [f"・{it['text']} {cite(it)}" for it in result[key]] or ["・なし"]
        return "\n".join(lines)
    if kind == "report":
        return "\n".join(["【依頼者への報告文(下書き・未送信)】", f"件名: {result['subject']}",
                          *[it["text"] for it in result["paragraphs"]]])
    lines = ["【時系列(AI初稿・要確認)】"]
    lines += [f"{t['date'] or '日付不明'} {t['event']}({t['certainty']}) {cite(t)}" for t in result["timeline"]]
    lines.append("【争点】")
    lines += [f"・{i['issue']}: 当方 {i['our_position']} / 相手方 {i['their_position']} {cite(i)}"
              for i in result["issues"]]
    return "\n".join(lines)


# ---------------------------------------------------------------- フォルダ索引

@router.post("/cases/{case_id}/index", status_code=202)
def start_index(case_id: int, request: Request, conn=Depends(get_conn)):
    root = _case_folder(conn, case_id, session(request), request)
    job_id = jobs.create(conn, "index", case_id)
    lang = _settings(request).ocr_lang

    def work(c, progress):
        st = indexer.index_case(c, case_id, root, lang, progress)
        progress(f"完了: 新規・更新 {st['indexed']} / 変更なし {st['unchanged']} / 本文なし {st['empty']} / "
                 f"エラー {st['errors']} / 削除 {st['removed']}")

    _submit(request, job_id, work)
    return {"job_id": job_id}


@router.get("/cases/{case_id}/index")
def index_status(case_id: int, request: Request, conn=Depends(get_conn)):
    load_case(conn, case_id, session(request))
    files = db.rows(conn.execute(
        """SELECT f.*, (SELECT COUNT(*) FROM doc_chunks c WHERE c.file_id=f.id) AS chunks
           FROM doc_files f WHERE f.case_id=? ORDER BY f.rel_path""", (case_id,)))
    last = conn.execute("SELECT * FROM jobs WHERE case_id=? AND kind='index' ORDER BY id DESC LIMIT 1",
                        (case_id,)).fetchone()
    return {"files": files, "last_job": dict(last) if last else None}


@router.get("/cases/{case_id}/docsearch")
def docsearch(case_id: int, request: Request, q: str = Query(min_length=1, max_length=200), conn=Depends(get_conn)):
    load_case(conn, case_id, session(request))
    hits = indexer.search(conn, case_id, q)
    for h in hits:
        h.pop("text", None)
    return hits


# ---------------------------------------------------------------- 録音・文字起こし

@router.post("/cases/{case_id}/recordings", status_code=202)
def upload_recording(case_id: int, request: Request, file: UploadFile = File(...),
                     recorded_on: Optional[str] = Form(None), conn=Depends(get_conn)):
    load_case(conn, case_id, session(request))
    s = _settings(request)
    name = Path(file.filename or "recording.m4a").name
    if Path(name).suffix.lower() not in AUDIO_EXT:
        raise HTTPException(422, f"音声ファイルを選択してください({', '.join(sorted(AUDIO_EXT))})")
    if recorded_on and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", recorded_on):
        raise HTTPException(422, "録音日の形式が不正です")
    dest_dir = s.audio_dir / str(case_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{uuid.uuid4().hex[:12]}{Path(name).suffix.lower()}"
    size = 0
    with dest.open("wb") as out:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_AUDIO_BYTES:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, "ファイルが大きすぎます")
            out.write(chunk)
    tid = conn.execute("INSERT INTO transcripts(case_id, filename, stored_path, recorded_on, status, created_at) "
                       "VALUES(?,?,?,?,?,?)",
                       (case_id, name, str(dest), recorded_on or db.today().isoformat(), "待機", db.now())).lastrowid
    job_id = jobs.create(conn, "transcribe", case_id)
    transcriber = get_transcriber(s)

    def work(c, progress):
        c.execute("UPDATE transcripts SET status='処理中' WHERE id=?", (tid,))
        try:
            res = transcriber.transcribe(dest, progress)
        except Exception as e:
            c.execute("UPDATE transcripts SET status='失敗', message=? WHERE id=?", (str(e)[:500], tid))
            raise
        save_transcript(c, tid, res.segments, {}, duration=res.duration, engine=res.engine, message=res.message)
        return tid

    _submit(request, job_id, work)
    return {"job_id": job_id, "transcript_id": tid}


def save_transcript(conn, tid: int, segments: list[dict], speakers: dict, *, duration: float | None = None,
                    engine: str | None = None, message: str | None = None) -> None:
    t = dict(conn.execute("SELECT * FROM transcripts WHERE id=?", (tid,)).fetchone())
    fields = {"segments_json": json.dumps(segments, ensure_ascii=False),
              "speakers_json": json.dumps(speakers, ensure_ascii=False), "status": "完了"}
    if duration is not None:
        fields["duration"] = duration
    if engine is not None:
        fields["engine"] = engine
    if message is not None:
        fields["message"] = message
    conn.execute(f"UPDATE transcripts SET {','.join(k + '=?' for k in fields)} WHERE id=?", (*fields.values(), tid))
    indexer.add_transcript_chunks(conn, t["case_id"], tid, t["filename"], segments, speakers)
    dur = duration if duration is not None else (t["duration"] or 0)
    body = "\n".join(f"[{indexer.fmt_time(sg['start'])} {speakers.get(sg.get('speaker') or '', sg.get('speaker') or '話者不明')}] "
                     f"{sg['text']}" for sg in segments)
    content = f"録音「{t['filename']}」の文字起こし({indexer.fmt_time(dur)})\n{body}"
    minutes = max(1, round(dur / 60)) if dur else None
    if t["activity_id"] and conn.execute("SELECT 1 FROM activities WHERE id=?", (t["activity_id"],)).fetchone():
        conn.execute("UPDATE activities SET content=?, minutes=COALESCE(minutes, ?) WHERE id=?",
                     (content, minutes, t["activity_id"]))
    else:
        aid = conn.execute("INSERT INTO activities(case_id, date, kind, content, minutes, transcript_id, created_at) "
                           "VALUES(?,?,?,?,?,?,?)",
                           (t["case_id"], t["recorded_on"] or db.today().isoformat(), "面談", content, minutes, tid,
                            db.now())).lastrowid
        conn.execute("UPDATE transcripts SET activity_id=? WHERE id=?", (aid, tid))
    touch(conn, t["case_id"])


@router.get("/cases/{case_id}/recordings")
def list_recordings(case_id: int, request: Request, conn=Depends(get_conn)):
    load_case(conn, case_id, session(request))
    return db.rows(conn.execute(
        "SELECT id, filename, recorded_on, duration, status, message, engine, activity_id, created_at "
        "FROM transcripts WHERE case_id=? ORDER BY id DESC", (case_id,)))


def _transcript(conn, tid: int, sess) -> dict:
    r = conn.execute("SELECT * FROM transcripts WHERE id=?", (tid,)).fetchone()
    if not r:
        raise HTTPException(404, "見つかりません")
    load_case(conn, r["case_id"], sess)
    return dict(r)


@router.get("/transcripts/{tid}")
def get_transcript(tid: int, request: Request, conn=Depends(get_conn)):
    t = _transcript(conn, tid, session(request))
    t.pop("stored_path")
    t["segments"] = json.loads(t.pop("segments_json") or "[]")
    t["speakers"] = json.loads(t.pop("speakers_json") or "{}")
    return t


class TranscriptPatch(BaseModel):
    speakers: dict[str, str] = {}
    segments: Optional[list[dict]] = None


@router.put("/transcripts/{tid}")
def update_transcript(tid: int, body: TranscriptPatch, request: Request, conn=Depends(get_conn)):
    """話者名の付け替え・誤認識の修正。"""
    t = _transcript(conn, tid, session(request))
    if t["status"] != "完了":
        raise HTTPException(409, "文字起こしが完了していません")
    segs = json.loads(t["segments_json"] or "[]")
    if body.segments is not None:
        if len(body.segments) != len(segs):
            raise HTTPException(422, "セグメント数が一致しません")
        for old, new in zip(segs, body.segments):
            old["text"] = str(new.get("text", old["text"]))[:2000]
            old["speaker"] = str(new.get("speaker", old.get("speaker", "")))[:50]
    speakers = {str(k)[:50]: str(v)[:50] for k, v in body.speakers.items() if str(v).strip()}
    save_transcript(conn, tid, segs, speakers)
    return {"ok": True}


@router.get("/transcripts/{tid}/audio")
def transcript_audio(tid: int, request: Request, conn=Depends(get_conn)):
    t = _transcript(conn, tid, session(request))
    p = Path(t["stored_path"])
    if not p.is_file():
        raise HTTPException(404, "音声ファイルがありません")
    audit(conn, request, "録音の再生", "transcript", tid, t["case_id"])
    return FileResponse(p, filename=t["filename"], content_disposition_type="inline")


@router.delete("/transcripts/{tid}")
def delete_transcript(tid: int, request: Request, conn=Depends(get_conn)):
    sess = session(request)
    require_reauth(sess)
    t = _transcript(conn, tid, sess)
    conn.execute("DELETE FROM transcripts WHERE id=?", (tid,))
    if t["activity_id"]:
        conn.execute("DELETE FROM activities WHERE id=?", (t["activity_id"],))
    Path(t["stored_path"]).unlink(missing_ok=True)
    audit(conn, request, "録音の削除", "transcript", tid, t["case_id"], {"filename": t["filename"]})
    return {"ok": True}


# ---------------------------------------------------------------- 報酬・入金・預り金

FINANCE_KINDS = Literal["請求", "入金", "実費支出", "預り金受入", "預り金支出", "預り金返還"]


class FinanceIn(BaseModel):
    date: dt.date
    kind: FINANCE_KINDS
    category: str = "その他報酬"
    amount: int = Field(ge=0, le=10**10)
    note: str = ""


class FinancePatch(BaseModel):
    date: Optional[dt.date] = None
    kind: Optional[FINANCE_KINDS] = None
    category: Optional[str] = None
    amount: Optional[int] = Field(default=None, ge=0, le=10**10)
    note: Optional[str] = None


def _prep_finance(conn, case_id, data, create, item_id=None):
    kind = data.get("kind")
    cat = data.get("category")
    if create and kind in ("請求", "入金") and cat not in FEE_CATEGORIES + ["実費"]:
        raise HTTPException(422, f"請求・入金の区分は {'・'.join(FEE_CATEGORIES + ['実費'])} から選んでください")
    return data


child_routes("finance_entries", "finance", FinanceIn, FinancePatch, _prep_finance)


def finance_summary(rows: list[dict]) -> dict:
    def total(kind, pred=lambda r: True):
        return sum(r["amount"] for r in rows if r["kind"] == kind and pred(r))

    is_exp = lambda r: r["category"] == "実費"  # noqa: E731
    not_exp = lambda r: r["category"] != "実費"  # noqa: E731
    fees = {"billed": total("請求", not_exp), "received": total("入金", not_exp)}
    fees["receivable"] = max(0, fees["billed"] - fees["received"])     # 未収
    fees["advance"] = max(0, fees["received"] - fees["billed"])        # 請求前の入金(前受)
    by_cat = {}
    for r in rows:
        if r["kind"] in ("請求", "入金") and r["category"] != "実費":
            d = by_cat.setdefault(r["category"], {"billed": 0, "received": 0})
            d["billed" if r["kind"] == "請求" else "received"] += r["amount"]
    fees["by_category"] = by_cat
    exp = {"spent": total("実費支出"), "billed": total("請求", is_exp), "recovered": total("入金", is_exp)}
    exp["outstanding"] = exp["spent"] - exp["recovered"]
    dep = {"received": total("預り金受入"), "paid": total("預り金支出"), "returned": total("預り金返還")}
    dep["balance"] = dep["received"] - dep["paid"] - dep["returned"]
    warnings = []
    if dep["balance"] < 0:
        warnings.append("預り金の残高がマイナスです。記帳を確認してください。")
    return {"fees": fees, "expenses": exp, "deposit": dep, "warnings": warnings}


@router.get("/cases/{case_id}/finance")
def case_finance(case_id: int, request: Request, conn=Depends(get_conn)):
    load_case(conn, case_id, session(request))
    rows = db.rows(conn.execute("SELECT * FROM finance_entries WHERE case_id=? ORDER BY date, id", (case_id,)))
    return {"entries": rows, "summary": finance_summary(rows), "worktime": worktime(conn, case_id),
            "fee_categories": FEE_CATEGORIES, "expense_categories": EXPENSE_CATEGORIES}


# ---------------------------------------------------------------- 稼働・採算

def worktime(conn, case_id: int, date_from: str | None = None, date_to: str | None = None) -> dict:
    where, args = ["case_id=?", "minutes IS NOT NULL"], [case_id]
    if date_from:
        where.append("date>=?")
        args.append(date_from)
    if date_to:
        where.append("date<=?")
        args.append(date_to)
    w = " AND ".join(where)
    total = conn.execute(f"SELECT COALESCE(SUM(minutes),0) m, COUNT(*) n FROM activities WHERE {w}", args).fetchone()
    by_kind = {r["kind"]: r["m"] for r in conn.execute(
        f"SELECT kind, SUM(minutes) m FROM activities WHERE {w} GROUP BY kind ORDER BY m DESC", args)}
    by_month = {r["ym"]: r["m"] for r in conn.execute(
        f"SELECT substr(date,1,7) ym, SUM(minutes) m FROM activities WHERE {w} GROUP BY ym ORDER BY ym", args)}
    missing = conn.execute("SELECT COUNT(*) FROM activities WHERE case_id=? AND minutes IS NULL",
                           (case_id,)).fetchone()[0]
    return {"minutes": total["m"], "records": total["n"], "by_kind": by_kind, "by_month": by_month,
            "records_without_minutes": missing}


@router.get("/cases/{case_id}/worktime")
def case_worktime(case_id: int, request: Request, date_from: Optional[str] = None, date_to: Optional[str] = None,
                  conn=Depends(get_conn)):
    load_case(conn, case_id, session(request))
    return worktime(conn, case_id, date_from, date_to)


@router.get("/reports/profitability")
def profitability(request: Request, status: str = "受任,係属,終結", conn=Depends(get_conn)):
    """案件別の稼働時間と報酬(入金ベース・請求ベース)から時給換算する。実費・預り金は含めない。"""
    sess = session(request)
    sts = status.split(",")
    out = []
    for c in db.rows(conn.execute(
            f"SELECT id, title, field, status, sensitive FROM cases WHERE status IN ({','.join('?' * len(sts))})", sts)):
        rows = db.rows(conn.execute("SELECT * FROM finance_entries WHERE case_id=?", (c["id"],)))
        fs = finance_summary(rows)["fees"]
        wt = worktime(conn, c["id"])
        hours = wt["minutes"] / 60
        out.append({
            "case_id": c["id"], "title": masked_title(c, sess), "field": c["field"], "status": c["status"],
            "minutes": wt["minutes"], "records_without_minutes": wt["records_without_minutes"],
            "fees_received": fs["received"], "fees_billed": fs["billed"],
            "hourly_received": round(fs["received"] / hours) if hours else None,
            "hourly_billed": round(fs["billed"] / hours) if hours else None,
        })
    out.sort(key=lambda r: (r["hourly_received"] is None, r["hourly_received"] or 0))
    tot_min = sum(r["minutes"] for r in out)
    tot_rec = sum(r["fees_received"] for r in out)
    return {"cases": out, "total": {"minutes": tot_min, "fees_received": tot_rec,
                                    "hourly_received": round(tot_rec / (tot_min / 60)) if tot_min else None}}


@router.get("/reports/worktime")
def worktime_report(request: Request, date_from: str = Query(...), date_to: str = Query(...), conn=Depends(get_conn)):
    sess = session(request)
    rows = db.rows(conn.execute(
        """SELECT a.case_id, c.title, c.sensitive, SUM(a.minutes) m, COUNT(*) n FROM activities a
           JOIN cases c ON c.id=a.case_id WHERE a.minutes IS NOT NULL AND a.date BETWEEN ? AND ?
           GROUP BY a.case_id ORDER BY m DESC""", (date_from, date_to)))
    for r in rows:
        r["title"] = masked_title(r, sess)
    return {"cases": rows, "total_minutes": sum(r["m"] for r in rows)}


# ---------------------------------------------------------------- 設定(相談メモの様式)

class MemoTemplateIn(BaseModel):
    sections: list[str] = Field(min_length=1, max_length=20)


@router.get("/settings/memo-template")
def get_memo_template(conn=Depends(get_conn)):
    return {"sections": ai.memo_sections(conn), "default": ai.DEFAULT_MEMO_SECTIONS}


@router.put("/settings/memo-template")
def put_memo_template(body: MemoTemplateIn, conn=Depends(get_conn)):
    secs = [s.strip() for s in body.sections if s.strip()]
    if not secs:
        raise HTTPException(422, "見出しを1つ以上入力してください")
    db.set_setting(conn, "memo_sections", json.dumps(secs, ensure_ascii=False))
    return {"ok": True}

