"""Run the upstream Ableton MCP server over any transport."""

from __future__ import annotations

TRANSPORTS = ("stdio", "streamable-http", "sse")


def load_app():
    """Import the FastMCP app and register all upstream tools.

    Importing `ableton_live_mcp.tools` is what registers every @mcp.tool, so it
    must happen before we serve or list anything.
    """
    import ableton_live_mcp.tools  # noqa: F401  (registers tools)
    from ableton_live_mcp.app import mcp

    return mcp


def serve(
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
    path: str = "",
) -> None:
    if transport not in TRANSPORTS:
        raise ValueError(f"Unknown transport {transport!r}; use one of {', '.join(TRANSPORTS)}")
    mcp = load_app()
    if transport != "stdio":
        mcp.settings.host = host
        mcp.settings.port = port
        if path:
            mcp.settings.streamable_http_path = path
            mcp.settings.sse_path = path
        # Keep DNS-rebinding protection on for loopback, the only host we serve.
        # Real clients send Host as host:port, so allow the loopback names on any
        # port via the SDK's ":*" wildcard. Never widen this to "*".
        from mcp.server.transport_security import TransportSecuritySettings

        mcp.settings.transport_security = TransportSecuritySettings(
            allowed_hosts=["localhost:*", "127.0.0.1:*", "[::1]:*"],
            allowed_origins=["http://localhost:*", "http://127.0.0.1:*"],
        )
    mcp.run(transport=transport)
