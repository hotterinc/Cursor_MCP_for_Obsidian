#!/usr/bin/env bash
# Build standalone obsidian-context-mcp binary into obsidian-plugin/bin/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$ROOT/obsidian-plugin/bin"
PY_DIR="$ROOT/python"

if [[ -x "$PY_DIR/.venv/bin/python" ]]; then
  PYTHON="$PY_DIR/.venv/bin/python"
elif command -v uv >/dev/null 2>&1; then
  cd "$PY_DIR"
  uv sync --all-extras
  PYTHON="$(uv run which python)"
else
  PYTHON="${PYTHON:-python3}"
fi

cd "$PY_DIR"
"$PYTHON" -m pip install -q pyinstaller

"$PYTHON" -m PyInstaller --noconfirm obsidian-context-mcp.spec

mkdir -p "$OUT_DIR"
if [[ -f dist/obsidian-context-mcp ]]; then
  install -m 755 dist/obsidian-context-mcp "$OUT_DIR/obsidian-context-mcp"
elif [[ -f dist/obsidian-context-mcp.exe ]]; then
  install -m 755 dist/obsidian-context-mcp.exe "$OUT_DIR/obsidian-context-mcp.exe"
else
  echo "PyInstaller output not found in python/dist/" >&2
  exit 1
fi

echo "Built sidecar: $OUT_DIR/obsidian-context-mcp ($(du -h "$OUT_DIR/obsidian-context-mcp" | cut -f1))"
