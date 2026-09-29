# Build from the same locked environment and spec on every supported platform.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
. (Join-Path $Root "scripts/native.ps1")
$PyDir = Join-Path $Root "python"
$Python = Join-Path $PyDir ".venv/Scripts/python.exe"
$DistExe = Join-Path $PyDir "dist/obsidian-context-mcp.exe"
$OutDir = Join-Path $Root "obsidian-plugin/bin"
Push-Location $PyDir
try {
    if (Test-Path -LiteralPath $Python) {
        Invoke-Native $Python @("-m", "uv", "sync", "--locked", "--all-extras", "--group", "build")
    } else {
        Invoke-Native "uv" @("sync", "--locked", "--python", "3.12", "--all-extras", "--group", "build")
    }
    if (Test-Path -LiteralPath $DistExe) { Remove-Item -LiteralPath $DistExe -Force }
    Invoke-Native $Python @("-m", "PyInstaller", "--clean", "--noconfirm", "obsidian-context-mcp.spec")
    if (-not (Test-Path -LiteralPath $DistExe)) { throw "Fresh PyInstaller output missing: $DistExe" }
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
    Copy-Item -LiteralPath $DistExe -Destination (Join-Path $OutDir "obsidian-context-mcp.exe") -Force
} finally { Pop-Location }
