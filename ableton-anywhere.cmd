@echo off
REM Universal Ableton Live MCP launcher for shell-only agents.
REM Runs the installed `ableton-anywhere` command from the environment that owns it.
setlocal
set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"
if exist "%HERE%\Scripts\ableton-anywhere.exe" (
    "%HERE%\Scripts\ableton-anywhere.exe" %*
    exit /b %errorlevel%
)
if exist "%HERE%\.venv\Scripts\ableton-anywhere.exe" (
    "%HERE%\.venv\Scripts\ableton-anywhere.exe" %*
    exit /b %errorlevel%
)
where ableton-anywhere >nul 2>nul && (ableton-anywhere %* & exit /b %errorlevel%)
echo ableton-anywhere not found. Install with: uvx --from . ableton-anywhere --help 1>&2
exit /b 9009
