"""AI 機能: 出典つき質問・相談メモ・時系列/争点整理表。

流れ: 資料収集 → 匿名化 → (llm.send で漏れ検査・送信・記録) → 復元 → 出典照合
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from . import db, llm
from .anonymize import Anonymizer, build_for_case, nfkc

PROMPT_DIR = Path(__file__).parent / "prompts"
DEFAULT_MEMO_SECTIONS = ["事実関係", "争点", "依頼者の希望", "未確認事項", "次の対応"]
SOURCE_BUDGET_CHARS = 120_000
KINDS = ("ask", "memo", "timeline")


# ---------------------------------------------------------------- プロンプト

def load_prompt(kind: str) -> tuple[str, str]:
    """(system プロンプト, バージョン)。バージョンはプロンプト本文のハッシュ。"""
    text = (PROMPT_DIR / "common.md").read_text(encoding="utf-8") + "\n" + \
        (PROMPT_DIR / f"{kind}.md").read_text(encoding="utf-8")
    return text, hashlib.sha256(text.encode()).hexdigest()[:10]


_CITATIONS = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {"source_id": {"type": "string"}, "quote": {"type": "string"}},
        "required": ["source_id", "quote"],
        "additionalProperties": False,
    },
}
_ITEM = {
    "type": "object",
    "properties": {"text": {"type": "string"}, "citations": _CITATIONS},
    "required": ["text", "citations"],
    "additionalProperties": False,
}

SCHEMAS = {
    "ask": {
        "type": "object",
        "properties": {"answer": {"type": "array", "items": _ITEM},
                       "not_found": {"type": "array", "items": {"type": "string"}}},
        "required": ["answer", "not_found"],
        "additionalProperties": False,
    },
    "memo": {
        "type": "object",
        "properties": {
            "sections": {"type": "array", "items": {
                "type": "object",
                "properties": {"heading": {"type": "string"}, "items": {"type": "array", "items": _ITEM}},
                "required": ["heading", "items"], "additionalProperties": False}},
            "caveats": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["sections", "caveats"],
        "additionalProperties": False,
    },
    "timeline": {
        "type": "object",
        "properties": {
            "timeline": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "date_precision": {"type": "string", "enum": ["日", "月", "年", "不明"]},
                    "event": {"type": "string"},
                    "certainty": {"type": "string", "enum": ["確実", "争いあり", "要確認"]},
                    "note": {"type": "string"},
                    "citations": _CITATIONS,
                },
                "required": ["date", "date_precision", "event", "certainty", "note", "citations"],
                "additionalProperties": False}},
            "issues": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "issue": {"type": "string"},
                    "our_position": {"type": "string"},
                    "their_position": {"type": "string"},
                    "status": {"type": "string", "enum": ["争いあり", "争いなし", "不明"]},
                    "open_questions": {"type": "array", "items": {"type": "string"}},
                    "citations": _CITATIONS,
                },
                "required": ["issue", "our_position", "their_position", "status", "open_questions", "citations"],
                "additionalProperties": False}},
            "contradictions": {"type": "array", "items": _ITEM},
        },
        "required": ["timeline", "issues", "contradictions"],
        "additionalProperties": False,
    },
}


# ---------------------------------------------------------------- 資料の収集

def collect_sources(conn, case_id: int, query: str = "", include_files: bool = True,
                    budget: int = SOURCE_BUDGET_CHARS) -> tuple[list[dict], int]:
    """(出典候補, 予算超過で除外した件数)。"""
    srcs: list[dict] = []
    for r in conn.execute("SELECT * FROM doc_chunks WHERE case_id=? ORDER BY source_type DESC, rel_path, page, "
                          "t_start, id", (case_id,)):
        if r["source_type"] == "file" and not include_files:
            continue
        if r["source_type"] == "audio":
            srcs.append({"type": "audio", "label": f"{r['rel_path']} {r['loc']}", "transcript_id": r["transcript_id"],
                         "t_start": r["t_start"], "text": r["text"], "priority": 0})
        else:
            srcs.append({"type": "file", "label": f"{r['rel_path']} {r['loc']}", "rel_path": r["rel_path"],
                         "page": r["page"], "text": r["text"], "priority": 3})
    for r in conn.execute("SELECT * FROM activities WHERE case_id=? AND transcript_id IS NULL ORDER BY date, id",
                          (case_id,)):
        srcs.append({"type": "activity", "label": f"活動記録 {r['date']} {r['kind']}", "activity_id": r["id"],
                     "text": nfkc(r["content"]), "priority": 1})
    for r in conn.execute("""SELECT m.*, p.name AS pname, p.role AS prole FROM communications m
                             LEFT JOIN parties p ON p.id=m.party_id WHERE m.case_id=? ORDER BY m.date, m.id""",
                          (case_id,)):
        who = f"{r['prole']} {r['pname']}" if r["pname"] else ""
        srcs.append({"type": "communication", "label": f"連絡履歴 {r['date']} {r['channel']}({r['direction']}) {who}",
                     "comm_id": r["id"], "text": nfkc(r["summary"]), "priority": 2})
    c = conn.execute("SELECT memo FROM cases WHERE id=?", (case_id,)).fetchone()
    if c and c["memo"]:
        srcs.append({"type": "case_memo", "label": "案件メモ", "text": nfkc(c["memo"]), "priority": 1})

    total = sum(len(s["text"]) for s in srcs)
    omitted = 0
    if total > budget:
        if query:
            qg = _bigrams(nfkc(query))
            for s in srcs:
                s["score"] = len(qg & _bigrams(s["text"])) / (1 + len(qg))
            ranked = sorted(srcs, key=lambda s: (-s["score"], s["priority"]))
        else:
            ranked = sorted(srcs, key=lambda s: s["priority"])
        kept, used = [], 0
        for s in ranked:
            if used + len(s["text"]) <= budget:
                kept.append(s)
                used += len(s["text"])
        omitted = len(srcs) - len(kept)
        keep_ids = {id(s) for s in kept}
        srcs = [s for s in srcs if id(s) in keep_ids]
    for i, s in enumerate(srcs, 1):
        s["id"] = f"S{i}"
        s.pop("score", None)
    return srcs, omitted


def _bigrams(s: str) -> set[str]:
    s = re.sub(r"\s+", "", s)
    return {s[i:i + 2] for i in range(len(s) - 1)}


# ---------------------------------------------------------------- プロンプト本文の組立

def build_user_text(kind: str, case_row: dict, sources: list[dict], question: str, memo_sections: list[str]) -> str:
    lines = [f"<案件>\n分野: {case_row['field']}\n状態: {case_row['status']}\n</案件>", "<資料>"]
    for s in sources:
        lines.append(f"[{s['id']}] {s['label']}\n{s['text']}\n")
    lines.append("</資料>")
    if kind == "ask":
        lines.append(f"<質問>\n{question}\n</質問>")
    elif kind == "memo":
        lines.append("<見出し>\n" + "\n".join(f"{i}. {h}" for i, h in enumerate(memo_sections, 1)) + "\n</見出し>")
        if question:
            lines.append(f"<追加の指示>\n{question}\n</追加の指示>")
    elif question:
        lines.append(f"<追加の指示>\n{question}\n</追加の指示>")
    return "\n".join(lines)


def prepare(conn, case_id: int, kind: str, question: str = "") -> dict:
    """送信前の準備(匿名化まで)。プレビュー表示にも使う。"""
    if kind not in KINDS:
        raise ValueError("不明な種類")
    case_row = dict(conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone())
    an = build_for_case(conn, case_id)
    sources, omitted = collect_sources(conn, case_id, question if kind == "ask" else "")
    sections = memo_sections(conn)
    raw_user = build_user_text(kind, case_row, sources, question, sections)
    user_anon = an.anonymize(raw_user)
    for s in sources:
        s["text_anon"] = an.anonymize(s["text"])
    system, version = load_prompt(kind)
    return {"anonymizer": an, "sources": sources, "omitted": omitted, "user_anon": user_anon,
            "system": system, "version": version, "sections": sections,
            "leaks": an.find_leaks(system + "\n" + user_anon)}


def memo_sections(conn) -> list[str]:
    raw = db.get_setting(conn, "memo_sections")
    if raw:
        try:
            v = json.loads(raw)
            if isinstance(v, list) and all(isinstance(x, str) for x in v) and v:
                return v
        except json.JSONDecodeError:
            pass
    return DEFAULT_MEMO_SECTIONS


# ---------------------------------------------------------------- 実行

def run(conn, request, client, case_id: int, kind: str, question: str = "") -> int:
    p = prepare(conn, case_id, kind, question)
    an: Anonymizer = p["anonymizer"]
    public_sources = [{k: v for k, v in s.items() if k not in ("text_anon",)} for s in p["sources"]]
    rid, data = llm.send(conn, request, client=client, anonymizer=an, case_id=case_id, kind=kind,
                         question=question, system=p["system"], user_anonymized=p["user_anon"],
                         schema=SCHEMAS[kind], prompt_version=p["version"], sources=public_sources)
    result = finalize(kind, data, p["sources"], an)
    result["omitted_sources"] = p["omitted"]
    conn.execute("UPDATE ai_runs SET result_json=? WHERE id=?", (json.dumps(result, ensure_ascii=False), rid))
    return rid


def finalize(kind: str, data: dict, sources: list[dict], an: Anonymizer) -> dict:
    """出典照合をしてから復元する。"""
    by_id = {s["id"]: s for s in sources}
    stats = {"citations": 0, "verified": 0, "partial": 0, "unverified": 0, "missing_source": 0, "uncited_items": 0}

    def fix_citations(cits: list[dict]) -> list[dict]:
        out = []
        for c in cits or []:
            stats["citations"] += 1
            src = by_id.get(str(c.get("source_id", "")).strip("[] "))
            q = c.get("quote", "")
            entry = {"source_id": c.get("source_id"), "quote": an.restore(q)}
            if not src:
                entry.update(match="出典なし")
                stats["missing_source"] += 1
            else:
                m = match_quote(q, src.get("text_anon", src["text"]))
                entry.update(match=m, label=src["label"], type=src["type"],
                             **{k: src[k] for k in ("rel_path", "page", "transcript_id", "t_start", "activity_id",
                                                    "comm_id") if k in src})
                stats[{"一致": "verified", "部分一致": "partial"}.get(m, "unverified")] += 1
            out.append(entry)
        return out

    def walk_items(items: list[dict], text_key: str = "text") -> list[dict]:
        res = []
        for it in items or []:
            it = dict(it)
            it["citations"] = fix_citations(it.get("citations", []))
            if not it["citations"]:
                stats["uncited_items"] += 1
            for k, v in list(it.items()):
                if k != "citations":
                    it[k] = an.restore_obj(v)
            res.append(it)
        return res

    if kind == "ask":
        result = {"answer": walk_items(data.get("answer", [])), "not_found": an.restore_obj(data.get("not_found", []))}
    elif kind == "memo":
        result = {"sections": [{"heading": an.restore(s.get("heading", "")), "items": walk_items(s.get("items", []))}
                               for s in data.get("sections", [])],
                  "caveats": an.restore_obj(data.get("caveats", []))}
    else:
        result = {"timeline": walk_items(data.get("timeline", [])), "issues": walk_items(data.get("issues", [])),
                  "contradictions": walk_items(data.get("contradictions", []))}
    result["citation_stats"] = stats
    return result


def _norm_for_match(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    return re.sub(r"[\s「」『』\"'、。,.・…]", "", s)


def match_quote(quote: str, source_text: str) -> str:
    """引用が出典の本文に含まれるか。一致 / 部分一致 / 不一致 / 引用なし"""
    q, t = _norm_for_match(quote), _norm_for_match(source_text)
    if not q:
        return "引用なし"
    if q in t:
        return "一致"
    m = SequenceMatcher(None, q, t, autojunk=False).find_longest_match(0, len(q), 0, len(t))
    if m.size >= max(8, int(len(q) * 0.6)):
        return "部分一致"
    return "不一致"


def to_csv(result: dict) -> str:
    """時系列・争点整理表を CSV(Excel で開ける)に。"""
    import csv
    import io

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["時系列"])
    w.writerow(["日付", "精度", "出来事", "確度", "備考", "出典"])
    for t in result.get("timeline", []):
        w.writerow([t["date"], t["date_precision"], t["event"], t["certainty"], t["note"], _cite_text(t)])
    w.writerow([])
    w.writerow(["争点整理表"])
    w.writerow(["争点", "当方の主張", "相手方の主張", "状況", "未確認事項", "出典"])
    for i in result.get("issues", []):
        w.writerow([i["issue"], i["our_position"], i["their_position"], i["status"], " / ".join(i["open_questions"]),
                    _cite_text(i)])
    return "﻿" + buf.getvalue()


def _cite_text(item: dict) -> str:
    return " / ".join(f"{c.get('label', c.get('source_id'))}「{c.get('quote', '')}」" for c in item.get("citations", []))
