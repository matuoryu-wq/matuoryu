"""AI 出力(相談メモ・時系列・出典つき回答)の評価スクリプト。

プロンプトやモデルを変えたときの「悪化」を検出する。採点は機械判定できる項目を優先:
  - 当事者名が復元されて出力に現れるか(names)
  - 期待する日付が時系列に入っているか(dates)
  - 争点・未確認事項・次の対応に期待する事項があるか(sections / issues / contradictions / keywords)
  - 出典の引用が実際に資料に存在するか(citation_valid)
  - 匿名化した語が送信内容に含まれていないか(leaks: 1件でもあれば不合格)

使い方:
  python scripts/eval_ai.py --live --record eval-runs/2026-10-15      実APIで実行(費用がかかる)し応答を保存
  python scripts/eval_ai.py --replay eval-runs/2026-10-15             保存した応答で再採点(API不要)
  python scripts/eval_ai.py --live --save-baseline                    結果を基準として保存
  基準(tests/fixtures/eval/baseline.json)があれば比較し、悪化があれば終了コード1
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from app.ai import load_prompt  # noqa: E402
from app.conflicts import normalize_name  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
EVAL_SET = FIX / "eval" / "eval_set.json"
BASELINE = FIX / "eval" / "baseline.json"
TOKEN = "eval-token-0123456789abcdef"
CONTENT_METRICS = ("names", "sections", "dates", "issues", "contradictions", "keywords")


# ---------------------------------------------------------------- 採点

def _texts(obj, skip=("citations",)) -> list[str]:
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, list):
        return [t for x in obj for t in _texts(x, skip)]
    if isinstance(obj, dict):
        return [t for k, v in obj.items() if k not in skip for t in _texts(v, skip)]
    return []


def _ratio(patterns: list[str], text: str) -> float:
    if not patterns:
        return 1.0
    return sum(1 for p in patterns if re.search(p, text)) / len(patterns)


def forbidden_terms(case: dict) -> list[str]:
    terms = []
    for p in case.get("parties", []):
        for v in (p.get("name"), p.get("kana"), p.get("phone"), p.get("email"), p.get("address")):
            if v:
                terms.append(v)
                terms += [x for x in v.split() if len(x) >= 2]
    if case.get("case_number"):
        terms.append(case["case_number"])
    return [t for t in dict.fromkeys(terms) if len(normalize_name(t)) >= 2]


def count_leaks(payload: str, terms: list[str]) -> list[str]:
    flat = normalize_name(re.sub(r"【[^【】]*】", "|", payload))
    return [t for t in terms if normalize_name(t) in flat]


def score_item(item: dict, result: dict, payloads: list[str], forbidden: list[str]) -> dict:
    exp = item.get("expect", {})
    m: dict[str, float | int | list] = {}
    all_text = "\n".join(_texts(result))
    if "names" in exp:
        flat = all_text.replace(" ", "")
        m["names"] = sum(1 for n in exp["names"] if n.replace(" ", "") in flat) / len(exp["names"])
    if "sections" in exp:
        got = {s["heading"]: "\n".join(_texts(s["items"])) for s in result.get("sections", [])}
        pats = [(h, p) for h, ps in exp["sections"].items() for p in ps]
        m["sections"] = sum(1 for h, p in pats if re.search(p, got.get(h, ""))) / len(pats)
    if "dates" in exp:
        got_dates = {t.get("date", "") for t in result.get("timeline", [])}
        m["dates"] = sum(1 for d in exp["dates"] if d in got_dates) / len(exp["dates"])
    if "issues" in exp:
        m["issues"] = _ratio(exp["issues"], "\n".join(_texts(result.get("issues", []))))
    if "contradictions" in exp:
        m["contradictions"] = _ratio(exp["contradictions"], "\n".join(_texts(result.get("contradictions", []))))
    if "keywords" in exp:
        m["keywords"] = _ratio(exp["keywords"], "\n".join(_texts(result.get("answer", []))))
    st = result.get("citation_stats", {})
    total = st.get("citations", 0)
    m["citation_valid"] = round((st.get("verified", 0) + st.get("partial", 0)) / total, 3) if total else 0.0
    items = max(1, sum(1 for _ in _iter_items(result)))
    m["uncited_rate"] = round(st.get("uncited_items", 0) / items, 3)
    leaks = sorted({t for p in payloads for t in count_leaks(p, forbidden)})
    m["leaks"] = len(leaks)
    m["leaked_terms"] = leaks
    content = [m[k] for k in CONTENT_METRICS if k in m]
    m["overall"] = round((sum(content) / len(content) if content else 0) * 0.7 + m["citation_valid"] * 0.3, 3)
    return m


def _iter_items(result: dict):
    for key in ("answer", "timeline", "issues", "contradictions"):
        yield from result.get(key, [])
    for s in result.get("sections", []):
        yield from s.get("items", [])


def compare(current: dict, baseline: dict, tol: float = 0.05) -> list[str]:
    """悪化の一覧。匿名化漏れは基準に関係なく常に不合格。"""
    bad = []
    for item_id, cur in current["items"].items():
        if cur["metrics"].get("leaks"):
            bad.append(f"{item_id}: 匿名化漏れ {cur['metrics']['leaked_terms']}")
        base = baseline.get("items", {}).get(item_id)
        if not base:
            continue
        for k, v in cur["metrics"].items():
            if k in ("leaks", "leaked_terms") or not isinstance(v, (int, float)):
                continue
            b = base["metrics"].get(k)
            if b is None:
                continue
            worse = (v > b + tol) if k == "uncited_rate" else (v < b - tol)
            if worse:
                bad.append(f"{item_id}: {k} {b} → {v}")
    return bad


# ---------------------------------------------------------------- 実行

class RecordingLLM:
    """送信内容を記録し、必要なら応答を保存する。"""

    def __init__(self, inner, record_dir: Path | None, item_id: str):
        self.inner, self.record_dir, self.item_id = inner, record_dir, item_id
        self.model = inner.model
        self.payloads: list[str] = []

    def complete(self, system, user, schema, max_tokens=32000):
        self.payloads.append(system + "\n" + user)
        res = self.inner.complete(system, user, schema)
        if self.record_dir:
            self.record_dir.mkdir(parents=True, exist_ok=True)
            (self.record_dir / f"{self.item_id}.json").write_text(
                json.dumps({"text": res.text, "model": res.model}, ensure_ascii=False, indent=1), encoding="utf-8")
        return res


class ReplayLLM:
    model = "replay"

    def __init__(self, replay_dir: Path, item_id: str):
        self.path = replay_dir / f"{item_id}.json"

    def complete(self, system, user, schema, max_tokens=32000):
        from app.llm import LLMResult
        d = json.loads(self.path.read_text(encoding="utf-8"))
        return LLMResult(d["text"], d.get("model", "replay"))


def run_item(item: dict, make_llm, workdir: Path) -> tuple[dict, list[str], list[str]]:
    from fastapi.testclient import TestClient

    from app.config import Settings
    from app.main import create_app
    from conftest import load_mock
    from fake_llm import FakeTranscriber
    from fixtures.make_folder import build

    mock = json.loads((FIX / "mock_cases.json").read_text(encoding="utf-8"))
    case = next(c for c in mock["cases"] if c["title"] == item["case"])
    rec = json.loads((FIX / item["recording"]).read_text(encoding="utf-8")) if item.get("recording") else None
    llm = make_llm()
    docs = workdir / item["id"] / "docs"
    docs.mkdir(parents=True)
    settings = Settings(app_token=TOKEN, data_dir=workdir / item["id"] / "data", allowed_folder_roots=[docs],
                        llm_factory=lambda: llm, transcriber_factory=lambda: FakeTranscriber(rec), jobs_sync=True)
    client = TestClient(create_app(settings), headers={"x-cm": "1", "authorization": f"Bearer {TOKEN}"})
    cid = load_mock(client, {"cases": [case]})[case["title"]]
    if item.get("folder"):
        folder = build(docs / "folder")
        client.put(f"/api/cases/{cid}", json={"folder_path": str(folder)})
        client.post(f"/api/cases/{cid}/index")
    if rec:
        client.post(f"/api/cases/{cid}/recordings", files={"file": (rec["filename"], b"x", "audio/mp4")})
    job = client.post(f"/api/cases/{cid}/ai/run", json={"kind": item["kind"], "question": item.get("question", "")}).json()
    j = client.get(f"/api/jobs/{job['job_id']}").json()
    if j["status"] != "完了":
        raise RuntimeError(f"{item['id']}: {j['error']}")
    result = client.get(f"/api/ai/runs/{j['result_id']}").json()["result"]
    return result, llm.payloads, forbidden_terms(case)


def run_eval(make_inner, record_dir: Path | None = None, only: list[str] | None = None) -> dict:
    items = json.loads(EVAL_SET.read_text(encoding="utf-8"))["items"]
    out = {"created_at": dt.datetime.now().isoformat(timespec="seconds"),
           "prompt_versions": {k: load_prompt(k)[1] for k in ("ask", "memo", "timeline")}, "items": {}}
    with tempfile.TemporaryDirectory() as tmp:
        for item in items:
            if only and item["id"] not in only:
                continue
            result, payloads, forbidden = run_item(
                item, lambda: RecordingLLM(make_inner(item["id"]), record_dir, item["id"]), Path(tmp))
            out["items"][item["id"]] = {"metrics": score_item(item, result, payloads, forbidden)}
    vals = [v["metrics"]["overall"] for v in out["items"].values()]
    out["overall"] = round(sum(vals) / len(vals), 3) if vals else 0
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--live", action="store_true", help="実 API(.env の ANTHROPIC_API_KEY)で実行")
    g.add_argument("--replay", type=Path, help="保存済みの応答で再採点")
    ap.add_argument("--record", type=Path, help="応答の保存先(--live 時)")
    ap.add_argument("--baseline", type=Path, default=BASELINE)
    ap.add_argument("--save-baseline", action="store_true")
    ap.add_argument("--tolerance", type=float, default=0.05)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--out", type=Path, default=ROOT / "eval-results")
    a = ap.parse_args()

    if a.live:
        from app.config import load_settings
        from app.llm import get_client
        s = load_settings()
        if not s.anthropic_api_key:
            print("ANTHROPIC_API_KEY が .env にありません", file=sys.stderr)
            return 2
        print(f"実 API で評価します(モデル {s.ai_model}、{len(json.loads(EVAL_SET.read_text('utf-8'))['items'])}件)。")
        make_inner = lambda _id: get_client(s)  # noqa: E731
    else:
        make_inner = lambda item_id: ReplayLLM(a.replay, item_id)  # noqa: E731

    res = run_eval(make_inner, a.record, a.only)
    a.out.mkdir(parents=True, exist_ok=True)
    path = a.out / f"eval-{dt.datetime.now():%Y%m%d-%H%M%S}.json"
    path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"{'項目':24} " + " ".join(f"{k:>14}" for k in ("overall", "citation_valid", "leaks")))
    for item_id, v in res["items"].items():
        m = v["metrics"]
        print(f"{item_id:24} {m['overall']:>14} {m['citation_valid']:>14} {m['leaks']:>14}")
        for k in CONTENT_METRICS:
            if k in m:
                print(f"    {k}: {m[k]:.2f}")
    print(f"全体: {res['overall']}  結果: {path}")

    if a.save_baseline:
        a.baseline.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"基準を保存しました: {a.baseline}")
        return 0
    base = json.loads(a.baseline.read_text(encoding="utf-8")) if a.baseline.exists() else {"items": {}}
    if not base["items"]:
        print("基準がありません(--save-baseline で保存できます)。匿名化漏れのみ判定します。")
    bad = compare(res, base, a.tolerance)
    if bad:
        print("\n悪化を検出:")
        for b in bad:
            print("  - " + b)
        return 1
    print("悪化なし")
    return 0


if __name__ == "__main__":
    sys.exit(main())
