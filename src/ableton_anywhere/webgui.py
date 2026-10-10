"""Local web GUI for Ableton Live, served by `ableton-anywhere gui`.

A single-page app (bundled in static.py) that shows the live session, an
activity stream of everything the agent does, and a tool runner to drive Live.
It talks to Live in-process via the bridge, and every action is journalled so
the work is visible and replayable. Loopback-only; no auth (same trust model as
the Remote Script).
"""

from __future__ import annotations

import json
from functools import lru_cache

from . import bridge, journal


@lru_cache(maxsize=1)
def _index_html() -> str:
    from importlib.resources import files

    return files("ableton_anywhere.static").joinpath("index.html").read_text(encoding="utf-8")


def build_app():
    """Build the Starlette ASGI app (imports are lazy so the CLI stays lean)."""
    from starlette.applications import Starlette
    from starlette.responses import HTMLResponse, JSONResponse
    from starlette.routing import Route

    async def index(_request):
        return HTMLResponse(_index_html())

    async def api_session(_request):
        text, is_error = await bridge.call_tool("get_session_snapshot", {})
        if is_error:
            return JSONResponse({"connected": False, "error": text})
        try:
            return JSONResponse({"connected": True, "session": json.loads(text)})
        except json.JSONDecodeError:
            return JSONResponse({"connected": True, "session": {}, "raw": text})

    async def api_tools(_request):
        tools = await bridge.list_tools()
        return JSONResponse(
            [{"name": t["name"], "summary": t["summary"], "schema": t["schema"]} for t in tools]
        )

    async def api_activity(_request):
        return JSONResponse(journal.journal.recent(200))

    async def api_call(request):
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return JSONResponse({"ok": False, "error": "Body must be JSON."}, status_code=400)
        tool = body.get("tool")
        arguments = body.get("arguments") or {}
        if not tool or not isinstance(tool, str):
            return JSONResponse({"ok": False, "error": "Missing 'tool' (string)."}, status_code=400)
        if not isinstance(arguments, dict):
            return JSONResponse({"ok": False, "error": "'arguments' must be an object."}, status_code=400)

        text, is_error = await bridge.call_tool(tool, arguments)

        # Best-effort lightweight "state after" for replay (never fatal).
        state_after = None
        if not is_error:
            try:
                stext, serr = await bridge.call_tool("get_session_snapshot", {})
                if not serr:
                    snap = json.loads(stext)
                    state_after = {"tempo": snap.get("tempo"), "track_count": snap.get("track_count")}
            except Exception:  # noqa: BLE001
                state_after = None

        journal.journal.record(
            tool,
            arguments,
            ok=not is_error,
            result="" if is_error else text,
            error=text if is_error else "",
            state_after=state_after,
        )
        return JSONResponse({"ok": not is_error, "text": text})

    routes = [
        Route("/", index, methods=["GET"]),
        Route("/api/session", api_session, methods=["GET"]),
        Route("/api/tools", api_tools, methods=["GET"]),
        Route("/api/activity", api_activity, methods=["GET"]),
        Route("/api/call", api_call, methods=["POST"]),
    ]
    return Starlette(routes=routes)


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    import uvicorn

    app = build_app()
    print(f"Ableton web GUI:  http://{host}:{port}")
    print("Loopback only. Press Ctrl+C to stop.")
    uvicorn.run(app, host=host, port=port, log_level="warning")
