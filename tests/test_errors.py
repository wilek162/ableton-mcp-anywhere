import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ableton_anywhere import bridge  # noqa: E402


@pytest.mark.asyncio
async def test_call_tool_unknown_tool_returns_error_not_crash():
    """A bad tool name must surface as is_error=True, not raise."""
    text, is_error = await bridge.call_tool("no_such_tool_xyz", {})
    assert is_error is True
    assert "no_such_tool_xyz" in text


def test_friendly_error_for_connection_failure_points_to_doctor():
    from ableton_live_mcp.connection import AbletonNotConnectedError

    msg = bridge._friendly_error("get_session_info", AbletonNotConnectedError("refused"))
    assert "doctor" in msg
    assert "Control Surface" in msg


def test_friendly_error_generic_includes_type():
    msg = bridge._friendly_error("set_tempo", RuntimeError("boom"))
    assert "RuntimeError" in msg and "boom" in msg
