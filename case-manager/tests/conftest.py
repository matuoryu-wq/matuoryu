import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from fake_llm import FakeLLM, FakeTranscriber  # noqa: E402

TOKEN = "test-token-abcdefghijklmnop"
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def recording():
    return json.loads((FIXTURES / "recording_takahashi.json").read_text(encoding="utf-8"))


@pytest.fixture
def settings(tmp_path, fake_llm, recording):
    docs = tmp_path / "docs"
    docs.mkdir()
    return Settings(app_token=TOKEN, data_dir=tmp_path / "data", backup_dir=tmp_path / "backup",
                    backup_keep=3, allowed_folder_roots=[docs], reauth_minutes=10,
                    llm_factory=lambda: fake_llm, transcriber_factory=lambda: FakeTranscriber(recording),
                    jobs_sync=True)


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def anon(app):
    return TestClient(app)


@pytest.fixture
def client(app):
    c = TestClient(app, headers={"x-cm": "1"})
    r = c.post("/api/auth/login", json={"token": TOKEN})
    assert r.status_code == 200
    return c


@pytest.fixture
def mock_data():
    return json.loads((FIXTURES / "mock_cases.json").read_text(encoding="utf-8"))


def load_mock(client, data):
    ids = {}
    for case in data["cases"]:
        body = {k: v for k, v in case.items() if k not in ("parties", "activities", "deadlines", "todos")}
        cid = client.post("/api/cases", json=body).json()["id"]
        ids[case["title"]] = cid
        for p in case.get("parties", []):
            assert client.post(f"/api/cases/{cid}/parties", json=p).status_code == 201
        for a in case.get("activities", []):
            assert client.post(f"/api/cases/{cid}/activities", json=a).status_code == 201
        for d in case.get("deadlines", []):
            assert client.post(f"/api/cases/{cid}/deadlines", json=d).status_code == 201
        for t in case.get("todos", []):
            assert client.post(f"/api/cases/{cid}/todos", json=t).status_code == 201
    return ids


@pytest.fixture
def loaded(client, mock_data):
    return load_mock(client, mock_data)
