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


async def call_tool(name: str, arguments: dict[str, Any] | None = None) -> tuple[str, bool]:
    """Invoke one tool. Returns (text, is_error)."""
    mcp = load_app()
    blocks = await mcp.call_tool(name, arguments or {})
    if isinstance(blocks, tuple):
        content = blocks[0]
    else:  # pragma: no cover - older SDKs returned just the content list
        content = blocks
    chunks = []
    for block in content:
        chunks.append(block.text if hasattr(block, "text") else json.dumps(block))
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
