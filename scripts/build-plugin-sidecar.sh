#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/python"
UV="${UV:-uv}"
if [[ -x .venv/bin/python ]]; then
  .venv/bin/python -m uv sync --locked --all-extras --group build
else
  "$UV" sync --locked --python 3.12 --all-extras --group build
fi
rm -f dist/obsidian-context-mcp
.venv/bin/python -m PyInstaller --clean --noconfirm obsidian-context-mcp.spec
test -f dist/obsidian-context-mcp
mkdir -p "$ROOT/obsidian-plugin/bin"
install -m 755 dist/obsidian-context-mcp "$ROOT/obsidian-plugin/bin/obsidian-context-mcp"
