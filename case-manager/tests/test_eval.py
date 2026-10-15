"""評価スクリプト(プロンプト変更時の悪化検出)のテスト。外部 API は使わない。"""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import eval_ai  # noqa: E402
from fake_llm import FakeLLM  # noqa: E402


def test_eval_runs_with_fake_llm(tmp_path):
    res = eval_ai.run_eval(lambda _id: FakeLLM(), record_dir=tmp_path / "rec")
    assert set(res["items"]) == {"takahashi_memo", "takahashi_timeline", "takahashi_ask", "saito_memo",
                                 "takahashi_status", "takahashi_report"}
    for item_id, v in res["items"].items():
        m = v["metrics"]
        assert m["leaks"] == 0, (item_id, m["leaked_terms"])     # 送信内容に匿名化対象の語なし
        assert 0 <= m["overall"] <= 1
    tl = res["items"]["takahashi_timeline"]["metrics"]
    assert tl["dates"] >= 0.6                                       # PDF・請求書・メールの日付
    assert res["items"]["takahashi_memo"]["metrics"]["names"] == 1.0  # 復元された氏名
    assert len(list((tmp_path / "rec").glob("*.json"))) == 6

    # 保存した応答で再採点すると同じ結果
    res2 = eval_ai.run_eval(lambda item_id: eval_ai.ReplayLLM(tmp_path / "rec", item_id))
    for k in res["items"]:
        assert res2["items"][k]["metrics"] == res["items"][k]["metrics"]
    assert eval_ai.compare(res2, res) == []


def test_compare_detects_regression():
    base = {"items": {"a": {"metrics": {"overall": 0.8, "dates": 1.0, "citation_valid": 0.9, "uncited_rate": 0.0,
                                        "leaks": 0, "leaked_terms": []}}}}
    cur = copy.deepcopy(base)
    assert eval_ai.compare(cur, base) == []
    cur["items"]["a"]["metrics"]["dates"] = 0.6
    cur["items"]["a"]["metrics"]["uncited_rate"] = 0.3
    bad = eval_ai.compare(cur, base)
    assert any("dates" in b for b in bad) and any("uncited_rate" in b for b in bad)
    cur = copy.deepcopy(base)
    cur["items"]["a"]["metrics"].update(leaks=1, leaked_terms=["髙橋"])
    assert any("匿名化漏れ" in b for b in eval_ai.compare(cur, {"items": {}}))


def test_score_item_and_leak_counting():
    item = {"expect": {"names": ["髙橋 一郎"], "dates": ["2026-04-15", "2026-05-31"],
                       "issues": ["検収"], "contradictions": ["納品"]}}
    result = {"timeline": [{"date": "2026-04-15", "event": "髙橋一郎が納品", "citations": []}],
              "issues": [{"issue": "検収の有無", "citations": []}], "contradictions": [],
              "citation_stats": {"citations": 4, "verified": 2, "partial": 1, "uncited_items": 1}}
    forbidden = eval_ai.forbidden_terms({"parties": [{"name": "髙橋 一郎", "kana": "タカハシ イチロウ"}]})
    m = eval_ai.score_item(item, result, ["【依頼者1】は高橋さん(たかはし)"], forbidden)
    assert m["names"] == 1.0 and m["dates"] == 0.5 and m["issues"] == 1.0 and m["contradictions"] == 0.0
    assert m["citation_valid"] == 0.75
    assert m["leaks"] >= 2 and "髙橋" in m["leaked_terms"]   # 異体字・かなでも漏れとして数える


def test_eval_set_is_well_formed():
    data = json.loads(eval_ai.EVAL_SET.read_text(encoding="utf-8"))
    mock = json.loads((eval_ai.FIX / "mock_cases.json").read_text(encoding="utf-8"))
    titles = {c["title"] for c in mock["cases"]}
    for it in data["items"]:
        assert it["case"] in titles and it["kind"] in ("ask", "memo", "timeline", "status", "report") and it["expect"]
