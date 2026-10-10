"""Generate ready-to-paste MCP client configuration for the Ableton server.

Every config points at the same upstream server package, pinned to the version
this tool was built against, so the Live-side Remote Script and the tools always
match. `write` can also drop the config into place for the clients whose config
is a plain JSON object.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from .library import remote_scripts_dir

# Keep in lockstep with the dependency pin in pyproject.toml.
SERVER_PACKAGE = "mcp-server-ableton-live"
SERVER_VERSION = "1.8.1"
SERVER_KEY = "ableton"


def server_args() -> list[str]:
    return [f"{SERVER_PACKAGE}@{SERVER_VERSION}"]


@dataclass(frozen=True)
class Client:
    """An MCP host and how its configuration is shaped."""

    key: str
    name: str
    kind: str  # "json" | "toml" | "cmd"
    path: str  # config file path, or a command hint for kind="cmd"
    env: str  # "" | "claude" | "gemini"


CLIENTS: list[Client] = [
    Client("claude-desktop", "Claude Desktop", "json", "%APPDATA%\\Claude\\claude_desktop_config.json", "claude"),
    Client("cursor", "Cursor", "json", "%USERPROFILE%\\.cursor\\mcp.json", ""),
    Client("windsurf", "Windsurf", "json", "%USERPROFILE%\\.codeium\\windsurf\\mcp_config.json", ""),
    Client("cline", "Cline (VS Code)", "json", "%APPDATA%\\Code\\User\\globalStorage\\saoudrizwan.claude-dev\\settings\\cline_mcp_settings.json", ""),
    Client("continue", "Continue", "json", "%USERPROFILE%\\.continue\\config.json", ""),
    Client("codex", "OpenAI Codex", "toml", "%USERPROFILE%\\.codex\\config.toml", ""),
    Client("claude-code", "Claude Code", "cmd", "claude mcp add", "claude"),
    Client("vscode", "VS Code (Copilot)", "json", "%APPDATA%\\Code\\User\\mcp.json", ""),
    Client("gemini", "Gemini CLI", "json", "%USERPROFILE%\\.gemini\\settings.json", "gemini"),
    Client("json", "Generic JSON", "json", "", ""),
]


def _expand(path: str) -> Path | None:
    if not path:
        return None
    return Path(os.path.expandvars(path))


def get_client(key: str) -> Client:
    for client in CLIENTS:
        if client.key == key:
            return client
    raise KeyError(f"Unknown client {key!r}. Known: {', '.join(c.key for c in CLIENTS)}")


def config_path(client: Client) -> Path | None:
    return _expand(client.path)


def _user_library_env() -> str:
    """Resolved User Library, so the server never has to guess."""
    try:
        return str(remote_scripts_dir().parent)
    except (FileNotFoundError, OSError):
        return ""


def json_snippet(client: Client, key: str = SERVER_KEY) -> str:
    env = {"ABLETON_USER_LIBRARY": _user_library_env()} if client.env else None
    entry = {"command": "uvx", "args": server_args()}
    if env:
        entry["env"] = {k: v for k, v in env.items() if v}
    return json.dumps({key: entry}, indent=2)


def toml_snippet(key: str = SERVER_KEY) -> str:
    lines = [f"[mcp_servers.{key}]", 'command = "uvx"']
    args = ", ".join(json.dumps(a) for a in server_args())
    lines.append(f"args = [{args}]")
    lines += ["", f"[mcp_servers.{key}.env]"]
    lib = _user_library_env()
    if lib:
        lines.append(f'ABLETON_USER_LIBRARY = {json.dumps(lib)}')
    else:
        lines.append("# ABLETON_USER_LIBRARY = <your User Library path>")
    return "\n".join(lines)


def cmd_snippet(client: Client, key: str = SERVER_KEY) -> str:
    args = " ".join(server_args())
    lib = _user_library_env()
    env = f" ABLETON_USER_LIBRARY={json.dumps(lib)}" if lib and client.env == "claude" else ""
    if client.key == "claude-code":
        return f"claude mcp add --transport stdio {key} --env{env} -- uvx {args}".replace(" --env -- ", " -- ")
    return f"{client.path} {key} uvx {args}"


def snippet(client: Client, key: str = SERVER_KEY) -> str:
    if client.kind == "json":
        return json_snippet(client, key)
    if client.kind == "toml":
        return toml_snippet(key)
    return cmd_snippet(client, key)


def write(client: Client, key: str = SERVER_KEY) -> Path:
    """Merge this server into the client's config file (JSON clients only)."""
    if client.kind != "json":
        raise ValueError(f"{client.name} is configured with a command, not a JSON file. Use `config {client.key}`.")
    target = config_path(client)
    if target is None:
        raise ValueError(f"No known config path for {client.name}.")
    data: dict = {}
    if target.is_file():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            backup = target.with_suffix(target.suffix + ".bak")
            shutil.copy2(target, backup)
            data = {}
    entry = json.loads(json_snippet(client, key))[key]
    data.setdefault("mcpServers", {})[key] = entry
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(target)
    return target
