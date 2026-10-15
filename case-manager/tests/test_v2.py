"""v2: フォルダ索引・録音・AI(匿名化→送信→復元→出典照合)・稼働/報酬/採算。"""
import datetime as dt
import json
import sqlite3
import unicodedata

import pytest

from conftest import TOKEN
from fixtures.make_folder import build

TAKAHASHI = "髙橋 対 ㈱サンプル商事 売買代金請求"
# 匿名化されて API に送られてはならない語(当事者の氏名・読み・異体字・住所・電話・メール・会社名・事件番号、
# 依頼者が言い間違えた相手方担当者名「佐藤」を含む)
FORBIDDEN = ["髙橋", "高橋", "たかはし", "タカハシ", "一郎", "イチロウ", "サンプル商事", "サンプルショウジ",
             "佐東", "サトウ", "佐藤", "西新宿", "090-0000-0001", "ichiro@example.com", "sample-shoji", "1234号"]


@pytest.fixture
def case_with_folder(client, loaded, settings):
    cid = loaded[TAKAHASHI]
    folder = build(settings.allowed_folder_roots[0] / "髙橋事件")
    client.put(f"/api/cases/{cid}", json={"folder_path": str(folder)})
    # 依頼者の住所・メールを登録(匿名化対象)
    c = client.get(f"/api/cases/{cid}").json()
    pid = next(p["id"] for p in c["parties"] if p["role"] == "依頼者")
    client.put(f"/api/parties/{pid}", json={"address": "東京都新宿区西新宿1-2-3", "email": "ichiro@example.com"})
    return cid, folder


def job_done(client, job_id):
    j = client.get(f"/api/jobs/{job_id}").json()
    assert j["status"] == "完了", j
    return j


# ---------------------------------------------------------------- フォルダ索引

def test_index_folder(client, case_with_folder, loaded):
    cid, folder = case_with_folder
    job_done(client, client.post(f"/api/cases/{cid}/index").json()["job_id"])
    st = client.get(f"/api/cases/{cid}/index").json()
    files = {f["rel_path"]: f for f in st["files"]}
    assert files["契約/売買契約書.pdf"]["status"] == "ok" and files["契約/売買契約書.pdf"]["pages"] == 2
    assert files["打合せメモ.docx"]["status"] == "ok"
    assert files["相手方からのメール.eml"]["status"] == "ok"
    assert files["請求書.txt"]["status"] == "ok"
    scan = files["納品書_スキャン.pdf"]
    assert scan["status"] == "empty" and "スキャン" in scan["message"]

    hits = client.get(f"/api/cases/{cid}/docsearch", params={"q": "検収"}).json()
    locs = {(h["rel_path"], h["loc"]) for h in hits}
    assert ("契約/売買契約書.pdf", "p.2") in locs           # ページ番号つき
    assert any(h["rel_path"] == "打合せメモ.docx" for h in hits)
    assert "相手方からのメール.eml" in {h["rel_path"] for h in client.get(
        f"/api/cases/{cid}/docsearch", params={"q": "寸法の不具合"}).json()}
    assert client.get(f"/api/cases/{cid}/docsearch", params={"q": "甲"}).json()  # 2文字未満も可

    # 検索範囲は案件ごとに分離
    other = loaded["斎藤家 遺産分割(被相続人 斎藤 正)"]
    assert client.get(f"/api/cases/{other}/docsearch", params={"q": "検収"}).json() == []

    # 差分索引: 変更・削除の反映
    (folder / "請求書.txt").write_text("請求書 訂正版 金額 3,300,000円", encoding="utf-8")
    (folder / "打合せメモ.docx").unlink()
    job = job_done(client, client.post(f"/api/cases/{cid}/index").json()["job_id"])
    assert "削除 1" in job["progress"]
    assert client.get(f"/api/cases/{cid}/docsearch", params={"q": "訂正版"}).json()
    assert client.get(f"/api/cases/{cid}/docsearch", params={"q": "佐藤"}).json() == []

    # 横断検索でも本文がヒット
    res = client.get("/api/search", params={"q": "寸法の不具合"}).json()["results"]
    assert any(r["kind"] == "資料・録音" for r in res)


# ---------------------------------------------------------------- 録音

def upload(client, cid, name="相談録音_髙橋様.m4a"):
    r = client.post(f"/api/cases/{cid}/recordings", files={"file": (name, b"\x00fake-audio", "audio/mp4")},
                    data={"recorded_on": "2026-05-10"})
    assert r.status_code == 202, r.text
    return r.json()


def test_recording_to_activity(client, case_with_folder, settings):
    cid, _ = case_with_folder
    r = upload(client, cid)
    job_done(client, r["job_id"])
    t = client.get(f"/api/transcripts/{r['transcript_id']}").json()
    assert t["status"] == "完了" and len(t["segments"]) == 11 and t["duration"] == 412.0
    acts = client.get(f"/api/cases/{cid}").json()["activities"]
    act = next(a for a in acts if a["transcript_id"] == r["transcript_id"])
    assert act["date"] == "2026-05-10" and act["kind"] == "面談" and act["minutes"] == 7
    assert "[00:00:12 SPEAKER_01]" in act["content"]

    # 話者名の付け替え・誤認識の修正 → 活動記録・検索に反映
    segs = t["segments"]
    segs[1]["text"] = "はい、髙橋一郎です。"
    assert client.put(f"/api/transcripts/{t['id']}", json={
        "speakers": {"SPEAKER_00": "弁護士", "SPEAKER_01": "依頼者"}, "segments": segs}).status_code == 200
    act = next(a for a in client.get(f"/api/cases/{cid}").json()["activities"] if a["transcript_id"] == t["id"])
    assert "[00:00:12 依頼者]" in act["content"] and "はい、髙橋一郎です。" in act["content"]
    hits = client.get(f"/api/cases/{cid}/docsearch", params={"q": "320万円"}).json()
    assert hits[0]["source_type"] == "audio" and hits[0]["loc"].startswith("00:00:")

    a = client.get(f"/api/transcripts/{t['id']}/audio")
    assert a.status_code == 200 and a.content == b"\x00fake-audio"

    # 音声以外は拒否
    bad = client.post(f"/api/cases/{cid}/recordings", files={"file": ("x.exe", b"MZ", "application/octet-stream")})
    assert bad.status_code == 422


def test_delete_recording_requires_reauth(client, case_with_folder, settings):
    cid, _ = case_with_folder
    r = upload(client, cid)
    db = sqlite3.connect(settings.db_path)
    db.execute("UPDATE sessions SET reauth_at=?", ((dt.datetime.now() - dt.timedelta(hours=1)).isoformat(),))
    db.commit()
    db.close()
    assert client.delete(f"/api/transcripts/{r['transcript_id']}").status_code == 403
    client.post("/api/auth/reauth", json={"token": TOKEN})
    assert client.delete(f"/api/transcripts/{r['transcript_id']}").status_code == 200
    acts = client.get(f"/api/cases/{cid}").json()["activities"]
    assert not any(a.get("transcript_id") == r["transcript_id"] for a in acts)


# ---------------------------------------------------------------- AI(v2 完了条件)

def test_v2_end_to_end_no_leak(client, case_with_folder, fake_llm, settings):
    """録音1件とフォルダ1件で、匿名化→メモ・出典つき回答が通り、匿名化した語が送信内容に含まれない。"""
    cid, _ = case_with_folder
    job_done(client, client.post(f"/api/cases/{cid}/index").json()["job_id"])
    job_done(client, upload(client, cid)["job_id"])

    # 送信前プレビュー(外部送信なし)
    pv = client.post(f"/api/cases/{cid}/ai/preview", json={"kind": "memo"}).json()
    assert pv["leaks"] == [] and pv["sources"] >= 6 and not fake_llm.calls
    assert any(r["original"] == "髙橋 一郎" for r in pv["replacements"])

    run_ids = {}
    for kind, q in [("memo", ""), ("ask", "この事件の経緯は?"), ("timeline", "")]:
        j = job_done(client, client.post(f"/api/cases/{cid}/ai/run", json={"kind": kind, "question": q}).json()["job_id"])
        run_ids[kind] = j["result_id"]
    assert len(fake_llm.calls) == 3

    # 1) 送信内容に匿名化対象の語が含まれない(異体字・カナ・全角半角を正規化しても)
    for call in fake_llm.calls:
        payload = unicodedata.normalize("NFKC", call["system"] + call["user"])
        for w in FORBIDDEN:
            assert w not in payload, w
        assert "【依頼者1】" in payload and "【相手方1(法人)】" in payload
        assert "320万円" in payload and "2026年5月31日" in payload   # 事実関係は残る

    # 2) 送信ログ: 実際の送信内容がそのまま記録され、監査ログにも残る
    runs = {k: client.get(f"/api/ai/runs/{v}").json() for k, v in run_ids.items()}
    for k, call in zip(("memo", "ask", "timeline"), fake_llm.calls):
        assert runs[k]["sent_text"] == call["user"] and runs[k]["status"] == "完了"
    assert "mapping_json" not in runs["memo"]          # 置換表は画面に返さない
    actions = [a["action"] for a in client.get("/api/audit").json()]
    assert actions.count("AI送信") == 3

    # 3) 相談メモ: 事務所様式の見出し・復元・出典
    memo = runs["memo"]["result"]
    assert [s["heading"] for s in memo["sections"]] == ["事実関係", "争点", "依頼者の希望", "未確認事項", "次の対応"]
    first = memo["sections"][0]["items"][0]
    assert "髙橋 一郎" in first["text"] and "【" not in first["text"]   # 記号が元に戻っている
    assert first["citations"][0]["match"] == "一致"

    # 4) 出典つき回答: 出典がファイル名・ページ / 録音の時刻に対応し、照合結果が付く
    ans = runs["ask"]["result"]
    cits = [c for it in ans["answer"] for c in it["citations"]]
    good = [c for c in cits if c["match"] == "一致"]
    assert good and all(c.get("label") for c in good)
    assert any(c["type"] == "audio" and c["t_start"] is not None for c in good) or \
        any(c["type"] == "file" for c in good)
    assert any(c["match"] == "不一致" for c in cits)       # 捏造された引用は検出される
    assert any(c["match"] == "出典なし" for c in cits)     # 存在しない出典番号も検出される
    st = ans["citation_stats"]
    assert st["missing_source"] == 1 and st["unverified"] >= 1

    # 5) 時系列: 日付と出典(PDFのページ)
    tl = runs["timeline"]["result"]["timeline"]
    assert any(t["date"] == "2026-05-31" for t in tl)
    pdf = [c for t in tl for c in t["citations"] if c.get("rel_path") == "契約/売買契約書.pdf"]
    assert pdf and pdf[0]["page"] in (1, 2)
    csv = client.get(f"/api/ai/runs/{run_ids['timeline']}/csv")
    assert csv.status_code == 200 and "争点整理表" in csv.text

    # 6) 初稿を活動記録に保存
    assert client.post(f"/api/ai/runs/{run_ids['memo']}/save-activity").status_code == 201
    acts = client.get(f"/api/cases/{cid}").json()["activities"]
    assert any(a["content"].startswith("【相談メモ(AI初稿・要確認)】") for a in acts)

    # AI送信ログ
    log = client.get("/api/ai/log").json()
    assert len(log) == 3 and all(r["sent_chars"] > 0 for r in log)


def test_leak_blocks_sending(client, case_with_folder, fake_llm, settings):
    cid, _ = case_with_folder
    # 中黒入りの表記は置換されないが、漏れ検査で送信が止まる
    client.post(f"/api/cases/{cid}/activities", json={"date": "2026-06-01", "content": "髙・橋さんから電話"})
    pv = client.post(f"/api/cases/{cid}/ai/preview", json={"kind": "memo"}).json()
    assert pv["leaks"]
    job = client.get(f"/api/jobs/{client.post(f'/api/cases/{cid}/ai/run', json={'kind': 'memo'}).json()['job_id']}").json()
    assert job["status"] == "失敗" and "匿名化" in job["error"]
    assert fake_llm.calls == []
    db = sqlite3.connect(settings.db_path)
    st, sent = db.execute("SELECT status, sent_text FROM ai_runs").fetchone()
    assert st == "送信前停止" and sent == ""
    # 追加の匿名化語を登録すると送信できる
    client.post(f"/api/cases/{cid}/anon-terms", json={"term": "髙・橋", "category": "人物"})
    assert client.post(f"/api/cases/{cid}/ai/preview", json={"kind": "memo"}).json()["leaks"] == []


def test_ai_not_configured(app, client, settings, loaded):
    settings.llm_factory = None
    settings.anthropic_api_key = ""
    cid = loaded[TAKAHASHI]
    r = client.post(f"/api/cases/{cid}/ai/run", json={"kind": "memo"})
    assert r.status_code == 400 and "ANTHROPIC_API_KEY" in r.json()["detail"]
    assert client.get("/api/ai/status").json()["ai_configured"] is False


def test_ask_requires_question(client, loaded):
    cid = loaded[TAKAHASHI]
    assert client.post(f"/api/cases/{cid}/ai/run", json={"kind": "ask", "question": " "}).status_code == 422


def test_memo_template(client, case_with_folder, fake_llm):
    cid, _ = case_with_folder
    client.put("/api/settings/memo-template", json={"sections": ["相談内容", "法的問題点", "方針"]})
    j = job_done(client, client.post(f"/api/cases/{cid}/ai/run", json={"kind": "memo"}).json()["job_id"])
    res = client.get(f"/api/ai/runs/{j['result_id']}").json()["result"]
    assert [s["heading"] for s in res["sections"]] == ["相談内容", "法的問題点", "方針"]


def test_sensitive_case_ai_requires_reauth(client, loaded, settings):
    cid = loaded["刑事 窃盗被告事件(被告人 山﨑)"]
    db = sqlite3.connect(settings.db_path)
    db.execute("UPDATE sessions SET reauth_at=?", ((dt.datetime.now() - dt.timedelta(hours=1)).isoformat(),))
    db.commit()
    db.close()
    assert client.post(f"/api/cases/{cid}/ai/run", json={"kind": "memo"}).status_code == 403
    assert client.post(f"/api/cases/{cid}/ai/preview", json={"kind": "memo"}).status_code == 403


# ---------------------------------------------------------------- 報酬・稼働・採算

def test_finance_and_profitability(client, loaded):
    cid = loaded[TAKAHASHI]
    entries = [
        {"date": "2026-05-10", "kind": "請求", "category": "着手金", "amount": 330000},
        {"date": "2026-05-15", "kind": "入金", "category": "着手金", "amount": 330000},
        {"date": "2026-05-15", "kind": "預り金受入", "category": "実費預り", "amount": 50000},
        {"date": "2026-06-02", "kind": "預り金支出", "category": "印紙", "amount": 20000},
        {"date": "2026-06-02", "kind": "実費支出", "category": "郵券", "amount": 6000},
        {"date": "2026-06-30", "kind": "請求", "category": "実費", "amount": 6000},
        {"date": "2026-09-30", "kind": "請求", "category": "報酬金", "amount": 256000},
    ]
    for e in entries:
        assert client.post(f"/api/cases/{cid}/finance", json=e).status_code == 201
    assert client.post(f"/api/cases/{cid}/finance", json={"date": "2026-01-01", "kind": "入金", "category": "謎",
                                                          "amount": 1}).status_code == 422
    assert client.post(f"/api/cases/{cid}/finance", json={"date": "2026-01-01", "kind": "入金", "category": "着手金",
                                                          "amount": -1}).status_code == 422
    f = client.get(f"/api/cases/{cid}/finance").json()
    s = f["summary"]
    assert s["fees"] == {"billed": 586000, "received": 330000, "receivable": 256000, "advance": 0,
                         "by_category": {"着手金": {"billed": 330000, "received": 330000},
                                         "報酬金": {"billed": 256000, "received": 0}}}
    assert s["expenses"] == {"spent": 6000, "billed": 6000, "recovered": 0, "outstanding": 6000}
    assert s["deposit"] == {"received": 50000, "paid": 20000, "returned": 0, "balance": 30000}  # 預り金は分離
    # 稼働: 模擬データの活動(90分+30分)
    assert f["worktime"]["minutes"] == 120

    p = client.get("/api/reports/profitability").json()
    row = next(r for r in p["cases"] if r["case_id"] == cid)
    assert row["minutes"] == 120 and row["fees_received"] == 330000
    assert row["hourly_received"] == 165000 and row["hourly_billed"] == 293000

    w = client.get("/api/reports/worktime", params={"date_from": "2026-05-01", "date_to": "2026-05-31"}).json()
    assert w["total_minutes"] == 90   # 5月は髙橋事件の初回面談(90分)のみ
