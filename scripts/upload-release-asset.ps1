param(
    [string]$Tag = "",
    [string]$ZipPath = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
 . (Join-Path $Root "scripts/native.ps1")
$ManifestVersion = (Get-Content (Join-Path $Root "obsidian-plugin/manifest.json") -Raw | ConvertFrom-Json).version
if (-not $Tag) { $Tag = "v$ManifestVersion" }
if ($Tag -ne "v$ManifestVersion") { throw "Release tag differs from manifest version" }
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

Invoke-Native $gh @("release", "upload", $Tag, $ZipPath, "--clobber")
Write-Host "Uploaded to $Tag : $ZipPath"
