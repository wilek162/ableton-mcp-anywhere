# ableton-mcp-anywhere

One Ableton Live MCP server that works with **any** agent: Claude Desktop, Cursor,
Windsurf, Cline, Continue, VS Code, Gemini CLI, Codex, Claude Code, or a plain
shell. No IDE required.

It wraps [`wstierhout/ableton-live-mcp`](https://github.com/wstierhout/ableton-live-mcp)
(156 typed tools, tested on Live 12) and adds the two things every setup trips over:

1. **User Library auto-detection.** The stock installer only looks in
   `Documents/Ableton/User Library`. This reads Live's own `Library.cfg` to find a
   relocated library, so `setup` just works.
2. **Client config for every host.** `config <client>` prints ready-to-paste JSON/TOML,
   or writes it for you.

> Requires Ableton Live 11/12, Python 3.10+, and [`uv`](https://docs.astral.sh/uv/).

## Install

```bash
uv tool install --from . ableton-mcp-anywhere
```

Or run it without installing:

```bash
uvx --from . ableton-mcp <command>
```

## 60-second setup

```bash
ableton-mcp setup      # install the Remote Script into the detected User Library
ableton-mcp doctor     # confirm the bridge is healthy
```

Then in Ableton Live: **Settings > Tempo & MIDI > MIDI > Control Surface > AbletonMCP**,
with **Input: None** and **Output: None**. Restart Live after installing the script.
(On Windows you can also run `ableton-mcp.cmd setup`.)

> `setup` and `doctor` are the only steps that touch Live. Every other command is a
> normal MCP server launch, so your client config is a single line.

## Connect your client

```bash
ableton-mcp config <client>          # print the snippet
ableton-mcp config <client> --write  # write it into the config file (JSON clients)
```

Clients: `claude-desktop`, `cursor`, `windsurf`, `cline`, `continue`, `codex`,
`claude-code`, `vscode`, `gemini`, `json` (generic).

Claude Desktop / Cursor / Windsurf / Continue / VS Code / Gemini — `mcpServers` JSON:

```json
{
  "ableton": {
    "command": "uvx",
    "args": ["mcp-server-ableton-live@1.8.1"]
  }
}
```

OpenAI Codex — `~/.codex/config.toml`:

```toml
[mcp_servers.ableton]
command = "uvx"
args = ["mcp-server-ableton-live@1.8.1"]
```

Claude Code:

```bash
claude mcp add --transport stdio ableton -- uvx mcp-server-ableton-live@1.8.1
```

## Use it without any MCP client

The same tools are available straight from the shell:

```bash
ableton-mcp tools                        # list all tools + one-line summaries
ableton-mcp call get_session_info        # read the running Live set
ableton-mcp call set_tempo tempo=128     # invoke a tool with arguments
ableton-mcp call create_midi_track --file args.json
ableton-mcp schema --format openai       # export OpenAI function-calling schema
ableton-mcp schema --format anthropic    # export Anthropic tool schema
ableton-mcp system-prompt                # ready-made system prompt for your agent
```

This is how agents with no native MCP support (custom scripts, local LLMs, notebooks)
drive Live: `tools` + `call`, or hand `schema`/`system-prompt` to the agent.

## Run over HTTP instead of stdio

Some hosts want a URL rather than a launched process:

```bash
uv tool install --from '.[http]' ableton-mcp-anywhere
ableton-mcp serve --transport streamable-http --port 8000
# Streamable HTTP endpoint:  http://127.0.0.1:8000/mcp
# SSE transport:            ableton-mcp serve --transport sse --port 8000   -> /sse
```

It binds to loopback only and keeps DNS-rebinding protection on. Do not expose it to
a network: the server has full control of your Live set and no authentication.

## Commands

| Command | What it does |
| --- | --- |
| `setup [--user-library PATH] [--replace]` | Install the Remote Script (auto-detects the library) |
| `uninstall [--user-library PATH]` | Remove the Remote Script (backs it up) |
| `doctor [--json]` | Check install + Live bridge, exit non-zero on failure |
| `serve [--transport stdio|streamable-http|sse]` | Run the server |
| `config <client> [--write] [--key NAME]` | Print or write client config |
| `tools [--json]` | List tools for shell/agent use |
| `call <tool> [k=v ...] [--json J] [--file F]` | Invoke a tool |
| `schema [--format openai|anthropic|mcp]` | Export tool schemas |
| `system-prompt` | Print a system prompt describing the tools |

## Troubleshooting

- **User Library not found** — pass it explicitly: `ableton-mcp setup --user-library "E:\Documents\ABLETON\User Library"`,
  or set `ABLETON_USER_LIBRARY`.
- **`AbletonMCP` missing from the Control Surface list** — the folder must be named exactly
  `AbletonMCP`, and Live only scans scripts at startup, so restart it.
- **Every call times out** — a modal dialog is open in Live (e.g. the trial nag) and it
  freezes the Remote Script. Dismiss it and retry.
- **Port 9877 refused** — Live isn't running or the Control Surface isn't selected.
- **Two bridges on one port** — don't enable two Ableton MCP Control Surfaces at once;
  run `setup --replace` if you're switching servers.

## Notes

- The server is pinned to `mcp-server-ableton-live==1.8.1` so the Live-side script and
  the tools stay version-matched. Bump them together.
- Not affiliated with Ableton. This wrapper is MIT, and it wraps an MIT-licensed server.
