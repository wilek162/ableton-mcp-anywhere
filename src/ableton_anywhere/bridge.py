"""Bridge for agents with no native MCP client.

Anything that can run a shell command can drive Ableton: `tools` lists what is
available, `call` invokes a tool, and `schema` exports the tools in OpenAI or
Anthropic function-calling format for custom agents.
"""

from __future__ import annotations

import json
from typing import Any

from .server import load_app


async def list_tools() -> list[dict[str, Any]]:
    mcp = load_app()
    result = []
    for tool in await mcp.list_tools():
        description = (tool.description or "").strip()
        result.append(
            {
                "name": tool.name,
                "summary": description.splitlines()[0] if description else "",
                "description": description,
                "schema": tool.inputSchema,
            }
        )
    return result


def _friendly_error(name: str, exc: BaseException) -> str:
    """Turn a tool failure into an actionable message instead of a traceback."""
    text = (str(exc) or "").strip()
    etype = type(exc).__name__
    low = text.lower()
    connection_types = {
        "AbletonNotConnectedError",
        "AbletonTimeoutError",
        "AbletonConnectionLostError",
    }
    if etype in connection_types or "not connected" in low or "connection" in low:
        return (
            f"Could not reach Ableton Live while running '{name}'.\n"
            "Check that Live is open and 'AbletonMCP' is selected as a Control Surface\n"
            "(Settings > Tempo & MIDI > MIDI, Input/Output None), then run:\n"
            "  ableton-anywhere doctor"
        )
    if "unknown tool" in low:
        return f"Unknown tool '{name}'. Run `ableton-anywhere tools` to list them."
    return f"{name} failed ({etype}): {text or 'no details'}"


async def call_tool(name: str, arguments: dict[str, Any] | None = None) -> tuple[str, bool]:
    """Invoke one tool. Returns (text, is_error).

    The MCP SDK raises on failure (unknown tool, Live not connected, timeout),
    so we catch it and surface a clean, actionable message with is_error=True so
    the CLI exits non-zero instead of dumping a traceback.
    """
    mcp = load_app()
    try:
        result = await mcp.call_tool(name, arguments or {})
    except Exception as exc:  # noqa: BLE001 - convert any tool failure to a message
        return _friendly_error(name, exc), True
    content = result[0] if isinstance(result, tuple) else result
    chunks = [block.text if hasattr(block, "text") else json.dumps(block) for block in content]
    return "\n".join(chunks), False


def schema(tools: list[dict[str, Any]], fmt: str = "openai") -> Any:
    if fmt == "openai":
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["schema"],
                },
            }
            for t in tools
        ]
    if fmt == "anthropic":
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["schema"],
            }
            for t in tools
        ]
    if fmt == "mcp":
        return tools
    raise ValueError(f"Unknown schema format {fmt!r}; use openai, anthropic or mcp.")


def system_prompt(tools: list[dict[str, Any]]) -> str:
    from ableton_live_mcp.app import INSTRUCTIONS

    index = "\n".join(f"- {t['name']}: {t['summary']}" for t in tools)
    return f"{INSTRUCTIONS}\n\n# Tools\n{index}\n"
