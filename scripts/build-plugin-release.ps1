# Build a drop-in Obsidian plugin zip for GitHub releases (Windows).
param(
    [switch]$SkipSidecar
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PluginSrc = Join-Path $Root "obsidian-plugin"
$ManifestPath = Join-Path $PluginSrc "manifest.json"
$Version = if ($env:VERSION) { $env:VERSION } else {
    (Get-Content $ManifestPath -Raw | ConvertFrom-Json).version
}
$Dist = Join-Path $Root "dist\release"
$Stage = Join-Path $Dist "obsidian-context-mcp"
$Arch = if ([System.Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture -eq "Arm64") { "arm64" } else { "x64" }
$Platform = if ($env:RELEASE_PLATFORM) { $env:RELEASE_PLATFORM } else { "windows-$Arch" }
$ZipName = "obsidian-context-mcp-$Version-$Platform.zip"
$ZipPath = Join-Path $Dist $ZipName
$SidecarSrc = Join-Path $PluginSrc "bin\obsidian-context-mcp.exe"

Write-Host "==> Building plugin UI..."
Push-Location $PluginSrc
try {
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        npm install
        npm run build
    } else {
        Write-Host "npm not found - using committed main.js"
        if (-not (Test-Path "main.js")) { throw "main.js missing and npm unavailable" }
    }
} finally {
    Pop-Location
}

if (-not $SkipSidecar) {
    Write-Host "==> Building standalone vault-server binary..."
    & (Join-Path $Root "scripts\build-plugin-sidecar.ps1")
}

if (-not (Test-Path $SidecarSrc)) {
    throw "Sidecar binary not found: $SidecarSrc"
}

Write-Host "==> Staging release..."
if (Test-Path $Stage) { Remove-Item $Stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path (Join-Path $Stage "bin") | Out-Null

Copy-Item (Join-Path $PluginSrc "manifest.json") $Stage
Copy-Item (Join-Path $PluginSrc "main.js") $Stage
Copy-Item (Join-Path $PluginSrc "styles.css") $Stage
Copy-Item $SidecarSrc (Join-Path $Stage "bin\obsidian-context-mcp.exe")

$install = @"
# Obsidian Context MCP - install

1. Unpack the zip.
2. Copy folder `obsidian-context-mcp` to: `YourVault/.obsidian/plugins/`
3. Obsidian -> Settings -> Community plugins -> enable **Obsidian Context MCP**.
4. Plugin settings -> **Access scopes** -> create scope -> **Copy JSON** -> paste into Cursor `.cursor/mcp.json`.

Windows first run: if SmartScreen blocks `obsidian-context-mcp.exe`, choose More info -> Run anyway.
The `data/` folder (index, scopes, logs) is created on first run and is not included in the zip.

Build platform: $Platform
Version: $Version
"@
Set-Content -Path (Join-Path $Stage "INSTALL.md") -Value $install -Encoding UTF8

Write-Host "==> Creating zip..."
New-Item -ItemType Directory -Force -Path $Dist | Out-Null
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path $Stage -DestinationPath $ZipPath -CompressionLevel Optimal

$sizeMb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
Write-Host ""
Write-Host ('Release zip: {0} ({1} MB)' -f $ZipPath, $sizeMb)
Write-Host "Contents:"
Get-ChildItem $Stage -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($Stage.Length + 1)
    Write-Host "  $rel"
}
