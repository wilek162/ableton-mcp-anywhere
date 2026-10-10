# ableton-mcp-anywhere — one-line installer for Windows.
#
#   powershell -c "irm https://raw.githubusercontent.com/wilek162/ableton-mcp-anywhere/main/install.ps1 | iex"
#
# Installs uv if missing, then the `ableton-anywhere` command. Tries PyPI first
# and falls back to this GitHub repo, so it works before the first release too.
$ErrorActionPreference = "Stop"

function Ensure-Uv {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Host "uv already installed."
        return
    }
    Write-Host "Installing uv..."
    irm https://astral.sh/uv/install.ps1 | iex
    # The installer drops uv in ~/.local/bin; make it visible this session.
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

Ensure-Uv

Write-Host "Installing ableton-mcp-anywhere..."
uv tool install ableton-mcp-anywhere
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyPI install unavailable; installing from GitHub instead..."
    uv tool install "ableton-mcp-anywhere @ git+https://github.com/wilek162/ableton-mcp-anywhere.git"
    if ($LASTEXITCODE -ne 0) { throw "Install failed. See the messages above." }
}

# Ensure the command resolves in the current shell.
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"

Write-Host ""
Write-Host "Done. Next steps:"
Write-Host "  ableton-anywhere setup     # install the Ableton Remote Script"
Write-Host "  ableton-anywhere doctor    # verify the bridge"
Write-Host ""
Write-Host "If 'ableton-anywhere' is not found, open a new terminal (PATH refresh)."
