param(
    [string]$Tag = "v0.2.7",
    [string]$ZipPath = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $ZipPath) {
    $version = (Get-Content (Join-Path $Root "obsidian-plugin\manifest.json") -Raw | ConvertFrom-Json).version
    $ZipPath = Join-Path $Root "dist\release\obsidian-context-mcp-$version-windows-x64.zip"
}
if (-not (Test-Path $ZipPath)) {
    throw "Zip not found: $ZipPath (run scripts/build-plugin-release.ps1 first)"
}

$gh = "$env:ProgramFiles\GitHub CLI\gh.exe"
if (-not (Test-Path $gh)) { $gh = "gh" }

& $gh auth status *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Run once: gh auth login"
    exit 1
}

& $gh release upload $Tag $ZipPath --clobber
Write-Host "Uploaded to $Tag : $ZipPath"
