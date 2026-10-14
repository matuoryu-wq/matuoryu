"""模擬事件セット(tests/fixtures/mock_cases.json)を稼働中のサーバーに投入する(動作確認・練習用)。

使い方:  python scripts/load_demo.py [http://127.0.0.1:8765]
実事件のデータベースには投入しないこと。
"""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.config import load_settings  # noqa: E402

base = sys.argv[1] if len(sys.argv) > 1 else f"http://127.0.0.1:{load_settings().port}"
token = load_settings().app_token


def call(method, path, body=None):
    req = urllib.request.Request(base + "/api" + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"authorization": f"Bearer {token}", "x-cm": "1",
                                          "content-type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


data = json.loads((ROOT / "tests" / "fixtures" / "mock_cases.json").read_text(encoding="utf-8"))
for case in data["cases"]:
    body = {k: v for k, v in case.items() if k not in ("parties", "activities", "deadlines", "todos")}
    cid = call("POST", "/cases", body)["id"]
    for key, path in (("parties", "parties"), ("activities", "activities"), ("deadlines", "deadlines"), ("todos", "todos")):
        for item in case.get(key, []):
            call("POST", f"/cases/{cid}/{path}", item)
    print(f"投入: #{cid} {case['title']}")
