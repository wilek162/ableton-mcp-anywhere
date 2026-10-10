import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ableton_anywhere import bridge, cli, server  # noqa: E402


def test_transports_exposed():
    assert server.TRANSPORTS == ("stdio", "streamable-http", "sse")


def test_schema_openai_shape():
    tools = [{"name": "set_tempo", "summary": "x", "description": "Set tempo", "schema": {"type": "object"}}]
    out = bridge.schema(tools, "openai")[0]
    assert out["type"] == "function"
    assert out["function"]["name"] == "set_tempo"
    assert out["function"]["parameters"] == {"type": "object"}


def test_schema_anthropic_shape():
    tools = [{"name": "set_tempo", "summary": "x", "description": "d", "schema": {}}]
    out = bridge.schema(tools, "anthropic")[0]
    assert out["name"] == "set_tempo"
    assert out["input_schema"] == {}


def test_schema_unknown_format_raises():
    try:
        bridge.schema([], "bogus")
    except ValueError:
        return
    raise AssertionError("expected ValueError for unknown format")


def test_parser_parses_call_and_config():
    parser = cli.build_parser()
    args = parser.parse_args(["call", "set_tempo", "tempo=128"])
    assert args.tool == "set_tempo" and args.args == ["tempo=128"]
    args = parser.parse_args(["config", "cursor", "--write"])
    assert args.client == "cursor" and args.write is True


def test_parser_serve_defaults_to_stdio():
    parser = cli.build_parser()
    args = parser.parse_args(["serve"])
    assert args.transport == "stdio" and args.port == 8000
