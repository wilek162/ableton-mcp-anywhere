import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ableton_anywhere import journal  # noqa: E402
from ableton_anywhere.webgui import build_app  # noqa: E402


def test_journal_record_and_recent():
    j = journal.Journal()
    j.record("set_tempo", {"tempo": 120}, ok=True, result="ok")
    j.record("create_midi_track", {}, ok=False, error="boom")
    recent = j.recent()
    assert len(recent) == 2
    assert recent[0]["tool"] == "set_tempo" and recent[0]["ok"] is True
    assert recent[1]["tool"] == "create_midi_track" and recent[1]["ok"] is False


def test_journal_persists_to_jsonl(tmp_path):
    log = tmp_path / "journal.jsonl"
    j = journal.Journal(log_path=log)
    j.record("set_tempo", {"tempo": 128}, ok=True, result="ok")
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert "set_tempo" in lines[0]


def test_journal_clear():
    j = journal.Journal()
    j.record("x", {}, ok=True)
    j.clear()
    assert j.recent() == []


@pytest.fixture()
def client():
    # Use the shared journal so /api/call -> /api/activity is observable.
    journal.journal.clear()
    from starlette.testclient import TestClient

    return TestClient(build_app())


def test_index_serves_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Ableton Anywhere" in r.text
    assert "/api/session" in r.text


def test_api_tools_lists_tools(client):
    r = client.get("/api/tools")
    assert r.status_code == 200
    names = {t["name"] for t in r.json()}
    assert "get_session_info" in names and "set_tempo" in names


def test_api_session_graceful_without_live(client):
    r = client.get("/api/session")
    assert r.status_code == 200
    body = r.json()
    # With no Live running (CI/sandbox) it must report not-connected, not crash.
    assert "connected" in body


def test_api_call_records_and_reports_error(client):
    r = client.post("/api/call", json={"tool": "no_such_tool_xyz", "arguments": {}})
    assert r.status_code == 200
    assert r.json()["ok"] is False
    activity = client.get("/api/activity").json()
    assert any(a["tool"] == "no_such_tool_xyz" and a["ok"] is False for a in activity)


def test_api_call_validates_body(client):
    assert client.post("/api/call", json={"arguments": {}}).json()["ok"] is False
