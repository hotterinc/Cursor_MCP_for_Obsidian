#!/usr/bin/env bash
# Build standalone obsidian-context-mcp binary into obsidian-plugin/bin/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$ROOT/obsidian-plugin/bin"
PY_DIR="$ROOT/python"
LLAMA_INDEX="${LLAMA_INDEX:-https://abetlen.github.io/llama-cpp-python/whl/cpu}"
VENV_PYTHON="$PY_DIR/.venv/bin/python"
UV="${UV:-uv}"

cd "$PY_DIR"

if [[ ! -x "$VENV_PYTHON" ]]; then
  if ! command -v "$UV" >/dev/null 2>&1; then
    echo "uv is required to create the Python venv" >&2
    exit 1
  fi
  "$UV" python install 3.12
  "$UV" venv --python 3.12 .venv
fi

echo "==> Installing Python deps (llama-cpp CPU wheels)..."
"$UV" pip install --python "$VENV_PYTHON" pyinstaller
"$UV" pip install --python "$VENV_PYTHON" -e ".[dev]" --extra-index-url "$LLAMA_INDEX"

echo "==> Running PyInstaller..."
"$VENV_PYTHON" -m PyInstaller --noconfirm obsidian-context-mcp.spec

mkdir -p "$OUT_DIR"
if [[ -f dist/obsidian-context-mcp ]]; then
  install -m 755 dist/obsidian-context-mcp "$OUT_DIR/obsidian-context-mcp"
  echo "Built sidecar: $OUT_DIR/obsidian-context-mcp ($(du -h "$OUT_DIR/obsidian-context-mcp" | cut -f1))"
elif [[ -f dist/obsidian-context-mcp.exe ]]; then
  install -m 755 dist/obsidian-context-mcp.exe "$OUT_DIR/obsidian-context-mcp.exe"
  echo "Built sidecar: $OUT_DIR/obsidian-context-mcp.exe ($(du -h "$OUT_DIR/obsidian-context-mcp.exe" | cut -f1))"
else
  echo "PyInstaller output not found in python/dist/" >&2
  exit 1
fi
