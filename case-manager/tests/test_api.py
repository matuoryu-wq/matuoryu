import datetime as dt
import sqlite3

from fastapi.testclient import TestClient

from conftest import TOKEN

TODAY = dt.date.today()


# ---------------------------------------------------------------- 認証・セキュリティ

def test_requires_auth(anon):
    assert anon.get("/api/cases").status_code == 401
    assert anon.get("/api/health").status_code == 200
    assert anon.get("/").status_code == 200


def test_login_requires_csrf_header(anon):
    assert anon.post("/api/auth/login", json={"token": TOKEN}).status_code == 403


def test_wrong_token_and_lockout(anon):
    h = {"x-cm": "1"}
    for _ in range(5):
        assert anon.post("/api/auth/login", json={"token": "wrong"}, headers=h).status_code == 401
    assert anon.post("/api/auth/login", json={"token": TOKEN}, headers=h).status_code == 429


def test_mutation_requires_csrf_header(app, client):
    c = TestClient(app, cookies=client.cookies)
    assert c.post("/api/cases", json={"title": "x"}).status_code == 403
    assert client.post("/api/cases", json={"title": "x"}).status_code == 201


def test_bearer_token(app):
    c = TestClient(app, headers={"authorization": f"Bearer {TOKEN}"})
    assert c.get("/api/cases").status_code == 200
    c = TestClient(app, headers={"authorization": "Bearer nope"})
    assert c.get("/api/cases").status_code == 401


def test_logout(client):
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/cases").status_code == 401


def test_security_headers(client):
    r = client.get("/api/cases")
    assert r.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]


def test_secrets_not_exposed(client, settings):
    body = client.get("/api/settings").text + client.get("/api/meta").text + client.get("/api/dashboard").text
    assert TOKEN not in body
    db = sqlite3.connect(settings.db_path)
    dump = "\n".join(db.iterdump())
    assert TOKEN not in dump  # セッションはハッシュのみ保存


def _expire_reauth(settings):
    db = sqlite3.connect(settings.db_path)
    old = (dt.datetime.now() - dt.timedelta(hours=1)).isoformat(timespec="seconds")
    db.execute("UPDATE sessions SET reauth_at=?", (old,))
    db.commit()
    db.close()


def test_sensitive_case_requires_reauth(client, settings):
    cid = client.post("/api/cases", json={"title": "機微な事件", "sensitive": True}).json()["id"]
    client.post(f"/api/cases/{cid}/parties", json={"role": "依頼者", "name": "秘密 太郎"})
    _expire_reauth(settings)

    r = client.get(f"/api/cases/{cid}")
    assert r.status_code == 403 and r.json()["detail"]["code"] == "reauth_required"
    # 一覧・検索では題名・内容が伏せられる
    lst = client.get("/api/cases").json()
    assert lst[0]["masked"] and "機微な事件" not in lst[0]["title"]
    s = client.get("/api/search", params={"q": "秘密"}).json()["results"]
    assert s and s[0]["masked"] and s[0]["snippet"] == "" and "機微な事件" not in s[0]["case_title"]
    # 子要素の変更も拒否
    assert client.post(f"/api/cases/{cid}/activities",
                       json={"date": str(TODAY), "content": "x"}).status_code == 403

    assert client.post("/api/auth/reauth", json={"token": "bad"}).status_code == 401
    assert client.post("/api/auth/reauth", json={"token": TOKEN}).status_code == 200
    assert client.get(f"/api/cases/{cid}").status_code == 200
    actions = [a["action"] for a in client.get("/api/audit").json()]
    assert "機微案件の閲覧" in actions and "再認証" in actions


def test_delete_case_requires_reauth(client, settings):
    cid = client.post("/api/cases", json={"title": "削除対象"}).json()["id"]
    _expire_reauth(settings)
    assert client.delete(f"/api/cases/{cid}").status_code == 403
    client.post("/api/auth/reauth", json={"token": TOKEN})
    assert client.delete(f"/api/cases/{cid}").status_code == 200
    assert client.get(f"/api/cases/{cid}").status_code == 404


# ---------------------------------------------------------------- CRUD

def test_case_crud_and_checklist(client):
    r = client.post("/api/cases", json={"title": "テスト事件", "field": "相続", "status": "受任",
                                        "accepted_on": "2026-10-01"})
    assert r.status_code == 201
    cid = r.json()["id"]
    c = client.get(f"/api/cases/{cid}").json()
    labels = [i["label"] for i in c["checklist"]]
    assert any("利益相反" in x for x in labels) and any("熟慮期間" in x for x in labels)
    assert any("委任契約" in x for x in labels) and any("本人確認" in x for x in labels)
    assert any("着手金" in x for x in labels)

    item = c["checklist"][0]["id"]
    assert client.put(f"/api/checklist/{item}", json={"done": True}).status_code == 200
    assert client.get(f"/api/cases/{cid}").json()["checklist"][0]["done"] == 1

    assert client.put(f"/api/cases/{cid}", json={"court": "東京家裁", "status": "終結"}).status_code == 200
    c = client.get(f"/api/cases/{cid}").json()
    assert c["court"] == "東京家裁" and c["status"] == "終結" and c["closed_on"] == str(TODAY)

    assert client.post("/api/cases", json={"title": ""}).status_code == 422
    assert client.post("/api/cases", json={"title": "x", "status": "不明"}).status_code == 422


def test_children_crud(client):
    cid = client.post("/api/cases", json={"title": "子要素"}).json()["id"]
    pid = client.post(f"/api/cases/{cid}/parties", json={"role": "依頼者", "name": "甲野 太郎",
                                                         "phone": "090"}).json()["id"]
    assert client.put(f"/api/parties/{pid}", json={"email": "a@example.com"}).status_code == 200

    aid = client.post(f"/api/cases/{cid}/activities",
                      json={"date": "2026-10-01", "kind": "面談", "content": "初回", "minutes": 60}).json()["id"]
    mid = client.post(f"/api/cases/{cid}/communications",
                      json={"party_id": pid, "date": "2026-10-02", "channel": "電話", "summary": "日程調整"}).json()["id"]
    tid = client.post(f"/api/cases/{cid}/todos",
                      json={"title": "回答確認", "status": "待ち", "waiting_for": "相手方回答待ち"}).json()["id"]
    did = client.post(f"/api/cases/{cid}/deadlines",
                      json={"kind": "期日", "title": "弁論準備", "due_date": "2026-11-01"}).json()["id"]

    c = client.get(f"/api/cases/{cid}").json()
    assert c["parties"][0]["email"] == "a@example.com"
    assert c["activities"][0]["minutes"] == 60
    assert c["communications"][0]["party_name"] == "甲野 太郎"
    assert c["todos"][0]["waiting_for"] == "相手方回答待ち"
    assert c["deadlines"][0]["confirmed"] == 1  # 手入力の期日は確定扱い

    # 他案件の当事者は指定できない
    other = client.post("/api/cases", json={"title": "別"}).json()["id"]
    assert client.post(f"/api/cases/{other}/communications",
                       json={"party_id": pid, "date": "2026-10-02", "summary": "x"}).status_code == 422

    assert client.put(f"/api/todos/{tid}", json={"status": "完了"}).status_code == 200
    assert client.get("/api/todos").json() == []
    for path in (f"/api/activities/{aid}", f"/api/communications/{mid}", f"/api/deadlines/{did}",
                 f"/api/parties/{pid}"):
        assert client.delete(path).status_code == 200
    c = client.get(f"/api/cases/{cid}").json()
    assert not (c["parties"] or c["activities"] or c["communications"] or c["deadlines"])
    assert client.delete("/api/activities/9999").status_code == 404


def test_deadline_calc_register_and_confirm(client):
    cid = client.post("/api/cases", json={"title": "控訴検討"}).json()["id"]
    calc = client.post("/api/deadline-calc", json={"event_date": "2026-10-03", "preset": "civil_appeal"}).json()
    assert calc["due"] == "2026-10-19" and calc["steps"] and calc["basis"]
    did = client.post(f"/api/cases/{cid}/deadlines",
                      json={"title": calc["title"], "due_date": calc["due"], "calc": calc}).json()["id"]
    d = client.get(f"/api/cases/{cid}").json()["deadlines"][0]
    assert d["confirmed"] == 0 and d["calc"]["steps"]
    notes = client.get("/api/notifications").json()
    assert any(n["type"] == "unconfirmed" for n in notes)

    assert client.post(f"/api/deadlines/{did}/confirm").status_code == 200
    d = client.get(f"/api/cases/{cid}").json()["deadlines"][0]
    assert d["confirmed"] == 1 and d["confirmed_at"]
    assert any(a["action"] == "期限の確定(承認)" for a in client.get("/api/audit").json())

    # 計算値から日付を手動変更すると備考に記録される
    client.put(f"/api/deadlines/{did}", json={"due_date": "2026-10-16"})
    d = client.get(f"/api/cases/{cid}").json()["deadlines"][0]
    assert "計算値 2026-10-19 から手動変更" in d["note"]


def test_deadline_calc_custom_and_custom_holiday(client):
    r = client.post("/api/deadline-calc", json={"event_date": "2026-10-01", "amount": 2, "unit": "week"})
    assert r.json()["due"] == "2026-10-15"
    client.post("/api/holidays", json={"date": "2026-10-15", "name": "庁舎停電"})
    r = client.post("/api/deadline-calc", json={"event_date": "2026-10-01", "amount": 2, "unit": "week"})
    assert r.json()["due"] == "2026-10-16"
    assert client.post("/api/deadline-calc", json={"event_date": "2026-10-01"}).status_code == 422
    assert client.post("/api/deadline-calc", json={"event_date": "2026-10-01", "preset": "nope"}).status_code == 422


def test_dashboard_and_notifications(client):
    cid = client.post("/api/cases", json={"title": "期限間近", "status": "係属"}).json()["id"]
    client.post(f"/api/cases/{cid}/deadlines", json={"title": "準備書面", "due_date": str(TODAY + dt.timedelta(days=1))})
    client.post(f"/api/cases/{cid}/deadlines", json={"title": "超過", "due_date": str(TODAY - dt.timedelta(days=2))})
    client.post(f"/api/cases/{cid}/deadlines", json={"title": "先の期日", "due_date": str(TODAY + dt.timedelta(days=40))})
    d = client.get("/api/dashboard").json()
    titles = [x["title"] for x in d["upcoming"]]
    assert titles == ["超過", "準備書面"]
    assert d["active_cases"][0]["title"] == "期限間近"
    assert d["last_backup_at"] is None
    texts = [n["text"] for n in d["notifications"]]
    assert any("期限超過" in t for t in texts) and any("バックアップ" in t for t in texts)


def test_stale_alert(client, settings):
    fresh = client.post("/api/cases", json={"title": "動いている", "status": "受任"}).json()["id"]
    stale = client.post("/api/cases", json={"title": "放置気味", "status": "受任"}).json()["id"]
    closed = client.post("/api/cases", json={"title": "終結済み", "status": "終結"}).json()["id"]
    client.post(f"/api/cases/{stale}/todos", json={"title": "回答確認", "status": "待ち", "waiting_for": "相手方回答待ち"})
    db = sqlite3.connect(settings.db_path)
    old = (dt.datetime.now() - dt.timedelta(days=45)).isoformat(timespec="seconds")
    db.execute("UPDATE cases SET updated_at=? WHERE id IN (?,?)", (old, stale, closed))
    db.commit()
    db.close()
    s = client.get("/api/stale").json()
    assert [x["id"] for x in s] == [stale]
    assert s[0]["idle_days"] >= 45 and "相手方回答待ち" in s[0]["waiting"]

    # 活動を記録すると放置から外れる
    client.post(f"/api/cases/{stale}/activities", json={"date": str(TODAY), "content": "催促の電話"})
    assert client.get("/api/stale").json() == []
    # 基準日数の変更
    assert fresh


def test_stale_days_setting(client, settings):
    cid = client.post("/api/cases", json={"title": "短期基準", "stale_days": 5}).json()["id"]
    db = sqlite3.connect(settings.db_path)
    db.execute("UPDATE cases SET updated_at=? WHERE id=?",
               ((dt.datetime.now() - dt.timedelta(days=6)).isoformat(timespec="seconds"), cid))
    db.commit()
    db.close()
    assert [x["id"] for x in client.get("/api/stale").json()] == [cid]
    client.put("/api/settings", json={"stale_days": 100})
    assert [x["id"] for x in client.get("/api/stale").json()] == [cid]  # 案件個別の設定が優先


# ---------------------------------------------------------------- 利益相反・検索(模擬事件セット)

def test_conflicts_with_mock_cases(client, loaded, mock_data):
    for q in mock_data["conflict_queries"]:
        r = client.post("/api/conflicts/check", json={"names": [{"name": q["name"], "kana": q["kana"]}]}).json()
        hits = r["results"][0]["hits"]
        got = sorted({h["case_title"] for h in hits})
        assert got == sorted(q["expect_cases"]), (q["name"], hits)
        if q["expect_adverse"]:
            assert any(h["adverse"] for h in hits), q["name"]
    hist = client.get("/api/conflicts/history").json()
    assert len(hist) == len(mock_data["conflict_queries"])
    assert client.put(f"/api/conflicts/{hist[0]['id']}", json={"conclusion": "該当なし・受任可"}).status_code == 200
    assert client.get("/api/conflicts/history").json()[0]["conclusion"] == "該当なし・受任可"


def test_conflict_exclude_own_case(client, loaded):
    cid = loaded["渡邊 労働事件(解雇無効)"]
    r = client.post("/api/conflicts/check", json={"names": [{"name": "渡辺健太"}], "exclude_case_id": cid}).json()
    assert r["hit_count"] == 0


def test_search(client, loaded):
    res = client.get("/api/search", params={"q": "320万円"}).json()["results"]
    assert {r["kind"] for r in res} == {"活動記録"}
    res = client.get("/api/search", params={"q": "渡辺"}).json()["results"]  # 表記ゆれ(渡邊)でも当事者がヒット
    assert any(r["kind"] == "当事者" for r in res)
    res = client.get("/api/search", params={"q": "令和8年(ワ)"}).json()["results"]
    assert any(r["kind"] == "案件" for r in res)
    res = client.get("/api/search", params={"q": "答弁書 待ち"}).json()["results"]
    assert any(r["kind"] == "TODO" for r in res)
    res = client.get("/api/search", params={"q": "100%_"}).json()["results"]
    assert res == []


def test_case_list_filters(client, loaded):
    all_open = client.get("/api/cases", params={"status": "相談,受任,係属"}).json()
    assert len(all_open) == 3
    assert all_open[0]["status"] == "係属"
    closed = client.get("/api/cases", params={"status": "終結"}).json()
    assert len(closed) == 1


# ---------------------------------------------------------------- 資料フォルダ

def test_files(client, settings, tmp_path):
    folder = settings.allowed_folder_roots[0] / "髙橋事件"
    (folder / "証拠").mkdir(parents=True)
    (folder / "訴状.txt").write_text("訴状本文", encoding="utf-8")
    (folder / "証拠" / "甲1.pdf").write_bytes(b"%PDF-1.4")
    (folder / "~$temp.docx").write_bytes(b"x")
    secret = tmp_path / "outside.txt"
    secret.write_text("外部", encoding="utf-8")

    # 許可ルート外は紐付け不可
    assert client.post("/api/cases", json={"title": "x", "folder_path": str(tmp_path)}).status_code == 422
    assert client.post("/api/cases", json={"title": "x", "folder_path": "relative/path"}).status_code == 422

    cid = client.post("/api/cases", json={"title": "資料あり", "folder_path": str(folder)}).json()["id"]
    r = client.get(f"/api/cases/{cid}/files").json()
    assert sorted(f["path"] for f in r["files"]) == ["訴状.txt", "証拠/甲1.pdf"]

    assert client.put(f"/api/cases/{cid}/files/note", json={"path": "訴状.txt", "note": "提出版"}).status_code == 200
    r = client.get(f"/api/cases/{cid}/files").json()
    assert {f["path"]: f["note"] for f in r["files"]}["訴状.txt"] == "提出版"
    assert any(x["kind"] == "資料メモ" for x in client.get("/api/search", params={"q": "提出版"}).json()["results"])

    r = client.get(f"/api/cases/{cid}/files/open", params={"path": "訴状.txt"})
    assert r.status_code == 200 and r.content.decode() == "訴状本文"
    # パストラバーサルは拒否
    assert client.get(f"/api/cases/{cid}/files/open", params={"path": "../../outside.txt"}).status_code == 404
    assert client.get(f"/api/cases/{cid}/files/open", params={"path": str(secret)}).status_code == 404
    assert any(a["action"] == "資料の閲覧" for a in client.get("/api/audit").json())


# ---------------------------------------------------------------- バックアップ・監査

def test_backup(client, settings):
    client.post("/api/cases", json={"title": "バックアップ対象"})
    for _ in range(4):
        r = client.post("/api/backup/run")
        assert r.status_code == 200
    files = sorted(settings.backup_dir.glob("cases-*.sqlite3"))
    assert 1 <= len(files) <= settings.backup_keep
    db = sqlite3.connect(files[-1])
    assert db.execute("SELECT title FROM cases").fetchone()[0] == "バックアップ対象"
    db.close()
    d = client.get("/api/dashboard").json()
    assert d["last_backup_at"]
    assert not any(n["type"] == "backup" for n in d["notifications"])


def test_audit_log_records_mutations(client):
    cid = client.post("/api/cases", json={"title": "監査"}).json()["id"]
    client.put(f"/api/cases/{cid}", json={"memo": "更新"})
    log = client.get("/api/audit").json()
    actions = [a["action"] for a in log]
    assert "POST /api/cases" in actions and f"PUT /api/cases/{cid}" in actions and "ログイン" in actions
    assert all(TOKEN not in (a["detail"] or "") for a in log)
