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

From PyPI (live once the first release is published — see *Releasing* below):

```bash
uv tool install ableton-mcp-anywhere
ableton-anywhere --version
```

One-shot, without installing:

```bash
uvx --from ableton-mcp-anywhere ableton-anywhere --help
```

From source (this repo):

```bash
uv tool install --from . '.[http]'   # [http] adds the server transports
# or
uvx --from . ableton-anywhere --help
```

On Windows you can also run `ableton-anywhere.cmd setup`.

## 60-second setup

```bash
ableton-anywhere setup      # install the Remote Script into the detected User Library
ableton-anywhere doctor     # confirm the bridge is healthy
```

Then in Ableton Live: **Settings > Tempo & MIDI > MIDI > Control Surface > AbletonMCP**,
with **Input: None** and **Output: None**. Restart Live after installing the script.
(On Windows you can also run `ableton-anywhere.cmd setup`.)

> `setup` and `doctor` are the only steps that touch Live. Every other command is a
> normal MCP server launch, so your client config is a single line.

## Connect your client

```bash
ableton-anywhere config <client>          # print the snippet
ableton-anywhere config <client> --write  # write it into the config file (JSON clients)
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
ableton-anywhere tools                        # list all tools + one-line summaries
ableton-anywhere call get_session_info        # read the running Live set
ableton-anywhere call set_tempo tempo=128     # invoke a tool with arguments
ableton-anywhere call create_midi_track --file args.json
ableton-anywhere schema --format openai       # export OpenAI function-calling schema
ableton-anywhere schema --format anthropic    # export Anthropic tool schema
ableton-anywhere system-prompt                # ready-made system prompt for your agent
```

This is how agents with no native MCP support (custom scripts, local LLMs, notebooks)
drive Live: `tools` + `call`, or hand `schema`/`system-prompt` to the agent.

## Run over HTTP instead of stdio

Some hosts want a URL rather than a launched process:

```bash
uv tool install --from '.[http]' ableton-mcp-anywhere
ableton-anywhere serve --transport streamable-http --port 8000
# Streamable HTTP endpoint:  http://127.0.0.1:8000/mcp
# SSE transport:            ableton-anywhere serve --transport sse --port 8000   -> /sse
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

## GitHub Codespaces (optional sandbox)

A Codespace is handy for testing packaging, the CLI, and the transports on a
clean Linux machine — but it **cannot reach Ableton Live**, which only runs as a
desktop app. Use it to develop and test; run `setup`/`doctor` against Live on
your own machine.

Codespaces need the `codespace` OAuth scope. If `gh codespace create` returns
`403 Must have admin rights`, add the scope once, then create one:

```bash
gh auth refresh -h github.com -s codespace    # one-time, opens a browser
gh codespace create -R <you>/ableton-mcp-anywhere --machine basicLinux32gb
gh codespace ssh -c <name>                    # or open it in the browser
```

A ready-made `.devcontainer/devcontainer.json` installs `uv`, syncs deps, and
builds the wheel on creation. The `Sandbox verify` GitHub Actions workflow runs
the same clean-room checks automatically on every push — no Codespace needed.

## Troubleshooting

- **User Library not found** — pass it explicitly: `ableton-anywhere setup --user-library "E:\Documents\ABLETON\User Library"`,
  or set `ABLETON_USER_LIBRARY`.
- **`AbletonMCP` missing from the Control Surface list** — the folder must be named exactly
  `AbletonMCP`, and Live only scans scripts at startup, so restart it.
- **Every call times out** — a modal dialog is open in Live (e.g. the trial nag) and it
  freezes the Remote Script. Dismiss it and retry.
- **Port 9877 refused** — Live isn't running or the Control Surface isn't selected.
- **Two bridges on one port** — don't enable two Ableton MCP Control Surfaces at once;
  run `setup --replace` if you're switching servers.

## Releasing (maintainers)

Publishing uses **PyPI Trusted Publishing** (OIDC) — no API token is stored in
the repo. One-time setup, then every `v*` tag publishes automatically.

1. Create a PyPI account and verify your email.
2. On PyPI: **Publishing → Add a pending publisher** with
   - PyPI project name: `ableton-mcp-anywhere`
   - Owner: `wilek162`, Repository: `ableton-mcp-anywhere`
   - Workflow name: `publish.yml`, Environment: `release`
3. Cut a release:

```bash
git tag v1.0.1 && git push origin v1.0.1
```

The `Publish to PyPI` workflow builds the wheel/sdist and publishes them. Watch
it under the repo's **Actions** tab. To sanity-check locally first:
`uv build && uvx twine check dist/*`.

## Notes

- The server is pinned to `mcp-server-ableton-live==1.8.1` so the Live-side script and
  the tools stay version-matched. Bump them together.
- Not affiliated with Ableton. This wrapper is MIT, and it wraps an MIT-licensed server.
