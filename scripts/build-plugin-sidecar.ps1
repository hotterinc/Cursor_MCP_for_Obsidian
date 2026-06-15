# Build standalone obsidian-context-mcp.exe into obsidian-plugin/bin/
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$OutDir = Join-Path $Root "obsidian-plugin\bin"
$PyDir = Join-Path $Root "python"
$VenvPython = Join-Path $PyDir ".venv\Scripts\python.exe"
$DistExe = Join-Path $PyDir "dist\obsidian-context-mcp.exe"
$OutExe = Join-Path $OutDir "obsidian-context-mcp.exe"
$LlamaIndex = "https://abetlen.github.io/llama-cpp-python/whl/cpu"

Push-Location $PyDir
try {
    if (-not (Test-Path $VenvPython)) {
        Write-Host "Creating venv (Python 3.12)..."
        uv python install 3.12
        uv venv --python 3.12 .venv
    }

    Write-Host "Installing dependencies..."
    uv pip install --python $VenvPython pyinstaller
    uv pip install --python $VenvPython -e ".[dev]" --extra-index-url $LlamaIndex

    Write-Host "Running PyInstaller (may take several minutes)..."
    & $VenvPython -m PyInstaller --noconfirm obsidian-context-mcp.spec
} finally {
    Pop-Location
}

if (-not (Test-Path $DistExe)) {
    throw "PyInstaller output not found: $DistExe"
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
Copy-Item $DistExe $OutExe -Force
$SizeMb = [math]::Round((Get-Item $OutExe).Length / 1MB, 1)
Write-Host ("Built sidecar: {0} ({1} MB)" -f $OutExe, $SizeMb)
