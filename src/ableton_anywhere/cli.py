"""One command to set up, run and configure the Ableton Live MCP server.

Subcommands:
  setup     Install the Live-side Remote Script (auto-detects the User Library)
  doctor    Report whether the install and the Live bridge are healthy
  serve     Run the MCP server (stdio by default; --transport http for a URL)
  config    Print (or --write) MCP client config for a specific host
  tools     List the available tools (for agents without an MCP client)
  call      Invoke one tool directly
  schema    Export tools as OpenAI/Anthropic function-calling schemas
  system-prompt  Print a ready-made system prompt describing the tools
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from . import __version__
from . import bridge, configs, server
from .library import find_user_library


def _cmd_setup(args) -> int:
    from ableton_live_mcp import cli as upstream

    try:
        resolved = find_user_library(args.user_library)
    except FileNotFoundError as exc:
        print(f"setup failed: {exc}", file=sys.stderr)
        return 1
    print(f"User Library: {resolved.path}  ({resolved.origin})")

    def _do_install(replace: bool) -> int:
        code = upstream.install(user_library=str(resolved.path), replace=replace)
        if code == 0:
            print(
                "\nNext: restart Ableton Live, then in Settings > Tempo & MIDI > MIDI pick "
                "'AbletonMCP' as a Control Surface with Input/Output set to None."
            )
        return code

    try:
        return _do_install(args.replace)
    except ValueError as exc:
        # Most often: a Remote Script from a *different* Ableton MCP tool is
        # already installed. Coexist safely instead of crashing or clobbering.
        print(f"\n{exc}")
        if getattr(args, "yes", False) or not sys.stdin.isatty():
            print(
                "\nRefusing to overwrite another tool's script. Re-run with --replace to\n"
                "back it up and switch to ableton-mcp-anywhere, or remove the other\n"
                "AbletonMCP Control Surface in Live first.",
                file=sys.stderr,
            )
            return 1
        answer = input(
            "\nReplace it with ableton-mcp-anywhere's script? "
            "(the existing script is backed up automatically) [y/N] "
        ).strip().lower()
        if answer not in ("y", "yes"):
            print("Aborted. Nothing was changed.")
            return 1
        try:
            return _do_install(True)
        except (OSError, ValueError) as exc2:
            print(f"setup failed: {exc2}", file=sys.stderr)
            return 1
    except OSError as exc:
        print(f"setup failed: {exc}", file=sys.stderr)
        return 1


def _cmd_uninstall(args) -> int:
    from ableton_live_mcp import cli as upstream

    resolved = find_user_library(args.user_library)
    return upstream.uninstall(user_library=str(resolved.path))


def _cmd_doctor(args) -> int:
    from ableton_live_mcp import cli as upstream

    try:
        resolved = find_user_library(args.user_library)
    except FileNotFoundError as exc:
        print(f"doctor failed: {exc}", file=sys.stderr)
        return 1
    return upstream.doctor(user_library=str(resolved.path), json_output=args.json)


def _cmd_serve(args) -> int:
    server.serve(transport=args.transport, host=args.host, port=args.port, path=args.path)
    return 0


def _cmd_config(args) -> int:
    client = configs.get_client(args.client)
    if args.write:
        target = configs.write(client, key=args.key)
        print(f"Wrote {args.key} to {target}")
        print(f"Restart {client.name} to load it.")
    else:
        print(f"# {client.name} -> {configs.config_path(client) or client.path}")
        print(configs.snippet(client, key=args.key))
    return 0


def _cmd_gui(args) -> int:
    from . import webgui

    try:
        webgui.run(host=args.host, port=args.port)
    except ImportError as exc:
        print("The web GUI needs its server extras. Install with:", file=sys.stderr)
        print("  uv tool install 'ableton-mcp-anywhere[http]'", file=sys.stderr)
        print(f"  (missing dependency: {exc})", file=sys.stderr)
        return 1
    return 0


async def _list_tools() -> list[dict]:
    return await bridge.list_tools()


def _cmd_tools(args) -> int:
    tools = asyncio.run(_list_tools())
    if args.json:
        print(json.dumps(tools, indent=2))
        return 0
    for tool in tools:
        print(f"{tool['name']}: {tool['summary']}")
    print(f"\n{len(tools)} tools. Use `ableton-anywhere call <tool> key=value ...` to invoke one.")
    return 0


def _cmd_call(args) -> int:
    arguments: dict = {}
    if args.json:
        arguments = json.loads(args.json)
    elif args.file:
        with open(args.file, encoding="utf-8-sig") as fh:
            arguments = json.load(fh)
    else:
        for item in args.args:
            key, _, value = item.partition("=")
            try:
                arguments[key] = json.loads(value)
            except ValueError:
                arguments[key] = value
    text, is_error = asyncio.run(bridge.call_tool(args.tool, arguments))
    print(text)
    return 1 if is_error else 0


def _cmd_schema(args) -> int:
    tools = asyncio.run(_list_tools())
    print(json.dumps(bridge.schema(tools, args.format), indent=2))
    return 0


def _cmd_system_prompt(_args) -> int:
    tools = asyncio.run(_list_tools())
    print(bridge.system_prompt(tools))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ableton-anywhere",
        description="Universal Ableton Live MCP server launcher (works with any agent/client).",
    )
    parser.add_argument("--version", "-V", action="version", version=f"ableton-mcp-anywhere {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("setup", "doctor"):
        p = sub.add_parser(name)
        p.add_argument("--user-library", help="User Library directory (auto-detected if omitted)")
        if name == "setup":
            p.set_defaults(func=_cmd_setup)
            p.add_argument("--replace", action="store_true", help="Replace a different existing script")
            p.add_argument("-y", "--yes", action="store_true", help="Never prompt; safe defaults (for scripts/CI)")
        else:
            p.set_defaults(func=_cmd_doctor)
            p.add_argument("--json", action="store_true", help="Emit the report as JSON")

    p = sub.add_parser("uninstall", help="Remove the Remote Script")
    p.add_argument("--user-library", help="User Library directory (auto-detected if omitted)")
    p.set_defaults(func=_cmd_uninstall)

    p = sub.add_parser("serve", help="Run the MCP server (stdio by default)")
    p.add_argument("--transport", choices=server.TRANSPORTS, default="stdio")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--path", default="", help="URL path for http/sse (default /mcp or /sse)")
    p.set_defaults(func=_cmd_serve)

    p = sub.add_parser("config", help="Print MCP client configuration")
    p.add_argument("client", choices=[c.key for c in configs.CLIENTS], nargs="?", default="json")
    p.add_argument("--write", action="store_true", help="Merge into the client config file")
    p.add_argument("--key", default=configs.SERVER_KEY, help="Server name in the config")
    p.set_defaults(func=_cmd_config)

    p = sub.add_parser("gui", help="Open the local web GUI (session view, activity, tool runner)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.set_defaults(func=_cmd_gui)

    p = sub.add_parser("tools", help="List available tools")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_cmd_tools)

    p = sub.add_parser("call", help="Invoke a tool")
    p.add_argument("tool")
    p.add_argument("args", nargs="*", help="key=value arguments")
    p.add_argument("--json", help="Arguments as a JSON object")
    p.add_argument("--file", help="Read arguments from a JSON file")
    p.set_defaults(func=_cmd_call)

    p = sub.add_parser("schema", help="Export tools as function-calling schemas")
    p.add_argument("--format", choices=["openai", "anthropic", "mcp"], default="openai")
    p.set_defaults(func=_cmd_schema)

    p = sub.add_parser("system-prompt", help="Print a ready-made system prompt")
    p.set_defaults(func=_cmd_system_prompt)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - clean CLI errors, traceback only when debugging
        if os.environ.get("ABLETON_ANYWHERE_DEBUG"):
            raise
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
