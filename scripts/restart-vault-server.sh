#!/usr/bin/env bash
set -euo pipefail

VAULT="${VAULT_PATH:-$HOME/Obsidian}"
DATA_DIR="$VAULT/.obsidian/plugins/obsidian-context-mcp/data"
PYTHON="${PYTHON_BIN:-$HOME/Cursor_MCP_for_Obsidian/python/.venv/bin/obsidian-context-mcp}"

# Stop existing vault-server for this vault
if [[ -f "$DATA_DIR/runtime.json" ]]; then
  PID=$(python3 -c "import json; print(json.load(open('$DATA_DIR/runtime.json'))['pid'])" 2>/dev/null || true)
  if [[ -n "${PID:-}" ]]; then
    kill "$PID" 2>/dev/null || true
    sleep 1
  fi
  rm -f "$DATA_DIR/runtime.json"
fi
rm -f "$DATA_DIR/locks/vault-server.lock"
rm -f "$HOME/Library/Application Support/obsidian-context-mcp/runtime/vault-server-"*.lock 2>/dev/null || true

exec "$PYTHON" vault-server \
  --vault-path "$VAULT" \
  --data-dir "$DATA_DIR" \
  --host 127.0.0.1 \
  --port 0
