@echo off
REM Universal Ableton Live MCP launcher for shell-only agents.
REM Runs the installed `ableton-mcp` command from the environment that owns it.
setlocal
set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"
if exist "%HERE%\Scripts\ableton-mcp.exe" (
    "%HERE%\Scripts\ableton-mcp.exe" %*
    exit /b %errorlevel%
)
if exist "%HERE%\.venv\Scripts\ableton-mcp.exe" (
    "%HERE%\.venv\Scripts\ableton-mcp.exe" %*
    exit /b %errorlevel%
)
where ableton-mcp >nul 2>nul && (ableton-mcp %* & exit /b %errorlevel%)
echo ableton-mcp not found. Install with: uvx --from . ableton-mcp --help 1>&2
exit /b 9009
