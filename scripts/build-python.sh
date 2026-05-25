#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/python"
uv sync --all-extras
uv run pyinstaller --onefile --name obsidian-context-mcp \
  --paths src \
  --hidden-import obsidian_context_mcp \
  src/obsidian_context_mcp/__main__.py
mkdir -p "$ROOT/apps/desktop/resources/python-sidecar"
cp dist/obsidian-context-mcp "$ROOT/apps/desktop/resources/python-sidecar/" 2>/dev/null || \
  cp dist/obsidian-context-mcp.exe "$ROOT/apps/desktop/resources/python-sidecar/" 2>/dev/null || true
echo "Python sidecar built into apps/desktop/resources/python-sidecar/"
