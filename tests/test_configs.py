import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ableton_anywhere import configs  # noqa: E402


def test_json_snippet_shape(monkeypatch):
    monkeypatch.setenv("ABLETON_USER_LIBRARY", r"E:\Documents\ABLETON\User Library")
    snippet = json.loads(configs.json_snippet(configs.get_client("claude-desktop")))
    entry = snippet["ableton"]
    assert entry["command"] == "uvx"
    assert entry["args"] == ["mcp-server-ableton-live@1.8.1"]
    # claude-desktop gets the resolved library so it never guesses.
    assert entry["env"]["ABLETON_USER_LIBRARY"].endswith("User Library")


def test_non_claude_clients_omit_env(monkeypatch):
    monkeypatch.setenv("ABLETON_USER_LIBRARY", r"E:\Documents\ABLETON\User Library")
    entry = json.loads(configs.json_snippet(configs.get_client("cursor")))["ableton"]
    assert "env" not in entry


def test_toml_snippet_is_valid_toml():
    text = configs.toml_snippet()
    parsed = None
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover
        tomllib = None
    if tomllib is not None:
        parsed = tomllib.loads(text)
    assert "mcp_servers.ableton" in text
    if parsed is not None:
        assert parsed["mcp_servers"]["ableton"]["command"] == "uvx"


def test_claude_code_command():
    text = configs.cmd_snippet(configs.get_client("claude-code"))
    assert text.startswith("claude mcp add --transport stdio")
    assert "mcp-server-ableton-live@1.8.1" in text


def test_write_merges_into_json(tmp_path, monkeypatch):
    monkeypatch.setenv("ABLETON_USER_LIBRARY", str(tmp_path / "User Library"))
    client = configs.get_client("cursor")
    target = tmp_path / "mcp.json"
    monkeypatch.setattr(configs, "config_path", lambda c: target if c.key == "cursor" else None)

    configs.write(client, key="ableton")
    data = json.loads(target.read_text(encoding="utf-8"))
    assert "ableton" in data["mcpServers"]

    # Writing again preserves existing servers.
    data["mcpServers"]["other"] = {"command": "x", "args": []}
    target.write_text(json.dumps(data), encoding="utf-8")
    configs.write(client, key="ableton")
    merged = json.loads(target.read_text(encoding="utf-8"))
    assert set(merged["mcpServers"]) >= {"ableton", "other"}


def test_unknown_client_raises():
    try:
        configs.get_client("nope")
    except KeyError:
        return
    raise AssertionError("expected KeyError for unknown client")
