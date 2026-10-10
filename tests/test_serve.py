import os
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest  # noqa: E402

mcp = pytest.importorskip("mcp")


@pytest.mark.asyncio
async def test_stdio_server_handshake_and_tools():
    """Drive `serve` as a real MCP client would, over stdio."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "ableton_anywhere.cli", "serve"],
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            assert init.serverInfo.name  # server identified itself
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            # A representative slice of the 156 tools must be registered.
            for expected in ("get_session_info", "set_tempo", "create_clip", "generate_drum_pattern"):
                assert expected in names


@pytest.mark.asyncio
async def test_call_tool_over_stdio():
    """A tool call round-trips through the stdio transport.

    This checks the transport + tool dispatch plumbing, which is what a host
    relies on. Whether Ableton is running only changes the *result*: with Live
    closed the tool returns an error explaining the Remote Script is unreachable,
    which is still a valid, well-formed MCP response.
    """
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "ableton_anywhere.cli", "serve"],
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_session_info", {})
            text = "".join(getattr(b, "text", "") for b in result.content)
            if result.isError:
                # Live closed (e.g. CI/Codespace): the server must say so clearly.
                assert "connect" in text.lower() or "ableton" in text.lower()
            else:
                # Live running: real session data comes back.
                assert "tempo" in text
