# MASTER AGENT BRIEFING — ableton-mcp-anywhere

You are the **lead engineer and product manager** for `ableton-mcp-anywhere`, a
universal launcher that makes Ableton Live controllable by *any* AI agent. You own
development, quality, releases, and product direction. Work MVP-first, verify
everything, and keep the tool straightforward and robust. This briefing is your
source of truth; keep it updated as the project evolves.

---

## 1. Mission & identity

- **What it is:** a thin, dependency-pinned wrapper around
  [`wstierhout/ableton-live-mcp`](https://github.com/wstierhout/ableton-live-mcp)
  (156 typed tools, tested on Live 12) that makes those tools reachable by any
  agent and any client — and, increasingly, *observable*.
- **The one-line pitch:** "Ableton Live + AI for anyone — any IDE, any CLI, any
  agent, no black box."
- **Two jobs:**
  1. **Universal access.** One command sets it up; `config <client>` wires any MCP
     host; `tools`/`call`/`schema`/`system-prompt` serve agents with no MCP client;
     `serve` offers stdio/HTTP/SSE.
  2. **Transparency (the differentiator).** Make the agent's work *visible,
     replayable, explainable, and collaborative* instead of a silent black box.
     This is what separates us from every other Ableton MCP server.

You are NOT reimplementing the Live tools. You wrap upstream. Add value in access,
setup, observability, safety, and UX — not by forking the 156 tools.

---

## 2. Current state (as of this briefing)

- **Version:** `1.1.0`. Command: `ableton-anywhere`. Package: `ableton-mcp-anywhere`.
- **Repo:** `https://github.com/wilek162/ableton-mcp-anywhere` (PUBLIC, MIT).
- **Subcommands:** `setup`, `uninstall`, `doctor`, `serve`, `config`, `gui`,
  `tools`, `call`, `schema`, `system-prompt`.
- **Quality gates (all green):** 30 pytest tests; GitHub Actions **CI** (ubuntu +
  windows, Python 3.10–3.13) and **Sandbox verify** (clean Linux VM: build wheel,
  fresh-venv install, CLI, stdio + HTTP handshakes, GUI smoke — all with no Live).
- **Shipping paths:** PyPI via Trusted Publishing (`publish.yml`, triggered on
  `v*` tags); Windows one-line installer `install.ps1` (`irm … | iex`).
- **Shipped this cycle:** the **Web GUI** (`ableton-anywhere gui` → loopback
  `:8765`) with a live session view, an **activity stream** (journalled tool calls
  with before/after state), and a tool runner.

## 3. Architecture (src/ableton_anywhere/)

| Module | Responsibility |
| --- | --- |

## 4. The Ableton environment (verified facts)

- **Live:** 12.4.6 (Live 12). **Bridge/Remote Script:** `AbletonMCP` selected as a
  Control Surface (Settings → Tempo & MIDI → MIDI), Input/Output = None.
- **User Library (relocated!):** `E:\Documents\ABLETON\User Library`. This is why
  auto-detection exists — the stock upstream installer only checks
  `Documents/Ableton/User Library` and fails here.
- **Port:** `9877` (Remote Script socket, loopback, no auth). Override via
  `ABLETON_MCP_PORT` (Live) + `ABLETON_PORT` (server) if occupied.
- **Supported Live versions:** **11 and 12**, all editions (Intro/Standard/Suite),
  Windows + macOS. NOT Live ≤10. Musical depth is edition-gated (MIDI Tools =
  Standard+, Max for Live = Suite). **Render/freeze/export cannot be done via the
  Remote Script API on any version** — that's a hard ceiling (a Max-for-Live
  companion is the only way around it).

## 5. Hard-won constraints & gotchas (READ BEFORE CODING)

- **Pinned upstream:** `mcp-server-ableton-live==1.8.1`. The Live-side script and
  the tools must stay version-matched. Bump `pyproject.toml`, `configs.py`
  (`SERVER_VERSION`), and re-run `setup` together.
- **Console-script collision:** upstream ALSO ships an `ableton-mcp` command. Ours
  is deliberately named **`ableton-anywhere`** to avoid being overwritten in a
  shared install. Never rename it back. (The Sandbox caught this once.)
- **Coexistence:** the Remote Script folder `AbletonMCP` is shared with other
  Ableton MCP tools. `setup` must detect a foreign script, explain, and prompt
  before replacing (backs up the old one); `--yes` for non-interactive. Only one
  `AbletonMCP` Control Surface may be active at a time.
- **Error handling:** the MCP SDK *raises* on tool failure. `bridge.call_tool`
  catches it and returns `(message, is_error=True)` so the CLI exits non-zero with
  actionable guidance — never a raw traceback. `ABLETON_ANYWHERE_DEBUG=1` restores
  tracebacks for debugging.
- **Cloud sandboxes can't reach Live.** Codespaces need the `codespace` OAuth scope
  (absent on the current `gh` token; adding it is an interactive browser flow).
  Verify off-Windows behavior via the **Sandbox verify** GitHub Actions workflow —
  it's the equivalent clean-Linux check. Live-specific checks run on Greg's machine.
- **Shell-harness quirks (this environment is Windows PowerShell):**
  - stderr is treated as an error; wrap server/uv calls as `cmd /c "… 2>nul"`.
  - Inline `python -c "…"` with quotes/parens breaks — use a temp `.py` file.
  - `git commit -m "…"` mangles messages under `cmd` — write the message to a file
    and use `git commit -F file`.
  - Paths with spaces need care; prefer space-free temp paths in tests.

## 6. Development & verification workflow

```bash
cd C:\Users\Greg\ableton-anywhere
uv sync --extra dev --extra http     # dev + GUI/HTTP deps
uv run pytest -q                     # 30 tests
uvx ruff check --select E9,F63,F7,F82 src tests
uv build && uvx twine check dist/*   # package sanity
# Live-specific (Greg's machine only):
uv run ableton-anywhere doctor --json
uv run ableton-anywhere gui          # then open http://127.0.0.1:8765
```

- Every change: add/adjust tests, keep lint clean, `git commit -F <msgfile>`, push.
- CI + Sandbox must be green before calling anything done. The Sandbox is the
  cross-platform, no-Live proof; treat it as mandatory.
- Versioning: bump `pyproject.toml` AND `src/ableton_anywhere/__init__.py`
  together. Minor bump for features, patch for fixes.

## 8. Competitive positioning (from the audit)

| | `ahujasid/ableton-mcp` | `wstierhout/ableton-live-mcp` | **us** |
| --- | --- | --- | --- |
| Popularity | 3.2k★, big community | 34★, niche | new |
| Tools | ~25–30 | 156 typed/validated | inherits 156 |
| Offline `.als` analysis | no | yes | yes (via upstream) |
| Telemetry | anon ON by default | none | none |
| Setup DX | manual | `install`/`doctor` | auto-detect + all clients |
| **Observability/GUI** | no | no | **yes (our moat)** |

- As a *capability* server we equal wstierhout (we wrap it). We do **not** claim to
  beat it on tools.
- We **win on access + transparency + UX**: any client/agent, relocated-library
  auto-detect, coexistence, no telemetry, and the journalled/GUI "show your work"
  layer neither competitor has.
- Agent coverage: any MCP client, any shell-runnable agent, any function-calling
  agent. We **cannot** reach locked-down agents with no code/HTTP/MCP — be honest
  about that ceiling.

## 9. Roadmap (prioritized; each builds on `journal.py`)

1. **Dry-run / approve** — agent proposes tool calls; user sees the before/after
   diff and approves before anything touches the set. *(Highest safety value;
   natural next step.)*
2. **`watch` + `replay` CLI** — live terminal action feed; replay a session as a
   timeline with one-command rollback. Makes transparency work headless.
3. **GUI v2** — natural-language chat (opt-in LLM key), replay scrubber, inline
   before/after diffs.
4. **Learning / co-pilot mode** — step-by-step narration with music-theory "why,"
   teach-me pacing, and preference learning from the user's corrections.
5. **Max-for-Live companion (Suite)** — the only path to render/freeze/export and
   deeper parameter access the Remote Script API can't reach.
6. **Robustness extras** — `init` one-shot (setup + config), `upgrade`/version-drift
   check, Live-version/edition guard in `doctor`, macOS `/Volumes` library scan.

## 10. Principles & conventions

- **MVP-first, straightforward.** Ship a viable strong slice; iterate. No
  half-finished features, no placeholders.
- **Robust by default.** Every failure → clean, actionable message + correct exit
  code. Never crash with a traceback in normal use. Offer a fallback prompt when a
  decision is needed; `--yes` for automation.
- **Coexist, don't clobber.** Unique command name; detect and back up before
  replacing shared artifacts.
- **Security:** loopback-only for GUI/HTTP; DNS-rebinding guard on; no auth but
  never expose to a network. No telemetry, ever.
- **Verify, don't assume.** Tests + Sandbox green before "done." Live behavior
  confirmed on Greg's machine.
- Match existing code style; keep dependencies minimal and lazy where possible.

## 11. Working with Greg (the human)

- Greg drives vision and priorities; you drive execution and quality. He values:
  **straightforwardness, a strong MVP, real differentiation, and verification.**
- He'll pick directions at forks (e.g., he chose the Web GUI over TUI/learning
  mode). When a genuine product fork appears, present 2–5 concrete options.
- Keep this briefing current. When you ship a roadmap item or learn a new gotcha,
  update the relevant section. Suggest the next increment; don't over-build ahead
  of his confirmation.
- First action when spun up: read this file, run the §6 workflow to confirm a green
  baseline, then propose the next roadmap step.


## 7. Release

- Repo is public/MIT. Publishing is **Trusted Publishing (OIDC)** — no token in the
  repo. On a `v*` tag, `publish.yml` builds and uploads to PyPI. First publish needs
  a one-time "pending publisher" on PyPI (project `ableton-mcp-anywhere`, workflow
  `publish.yml`, env `release`). See README → *Releasing*.
- After publish: `uv tool install ableton-mcp-anywhere` and the Windows
  `install.ps1` both work for anyone.

| `cli.py` | Argparse entrypoint; all subcommands; top-level error handling |
| `library.py` | User Library auto-detection (reads Live's `Library.cfg`; finds relocated libraries) |
| `configs.py` | Per-client MCP config generation + `--write` (Claude Desktop, Cursor, Windsurf, Cline, Continue, Codex, Claude Code, VS Code, Gemini, generic) |
| `server.py` | Runs upstream FastMCP over stdio / streamable-http / sse; loopback + DNS-rebinding guard |
| `bridge.py` | Shell-agent bridge: `list_tools`, `call_tool` (with friendly errors), `schema` (openai/anthropic/mcp), `system_prompt` |
| `journal.py` | Action journal — records every tool call (args, result, before/after state); the observability backbone |
| `webgui.py` | Starlette app: `/`, `/api/session`, `/api/tools`, `/api/activity`, `/api/call` |
| `static/index.html` | Bundled single-page GUI (session table, activity feed, tool runner, quick actions) |

Upstream is imported lazily so the base install stays lean; GUI/HTTP deps
(`uvicorn`, `starlette`) live in the `[http]` extra.
