#!/usr/bin/env bash
# Install self-contained Obsidian plugin: UI + Python server + data dir in one folder.
#
# Result layout in vault:
#   .obsidian/plugins/obsidian-context-mcp/
#     manifest.json, main.js, styles.css
#     server/.venv/          — Python vault-server (bundled)
#     data/                  — index, scopes, logs, models (created at runtime)
#
# Usage:
#   VAULT_PATH=~/Obsidian ./scripts/install-obsidian-plugin.sh
#   BUNDLE_MODE=venv|pyinstaller|skip   (default: venv)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VAULT="${VAULT_PATH:-$HOME/Obsidian}"
PLUGIN_SRC="$ROOT/obsidian-plugin"
PLUGIN_DST="$VAULT/.obsidian/plugins/obsidian-context-mcp"
BUNDLE_MODE="${BUNDLE_MODE:-venv}"
VENV_SRC="$ROOT/python/.venv"

echo "==> Building Obsidian plugin UI..."
cd "$PLUGIN_SRC"
npm install
npm run build

mkdir -p "$PLUGIN_DST"
install -m 644 "$PLUGIN_SRC/manifest.json" "$PLUGIN_DST/"
install -m 644 "$PLUGIN_SRC/main.js" "$PLUGIN_DST/"
install -m 644 "$PLUGIN_SRC/styles.css" "$PLUGIN_DST/"

case "$BUNDLE_MODE" in
  pyinstaller)
    echo "==> Building standalone server binary (PyInstaller)..."
    bash "$ROOT/scripts/build-plugin-sidecar.sh"
    mkdir -p "$PLUGIN_DST/bin"
    install -m 755 "$PLUGIN_SRC/bin/obsidian-context-mcp" "$PLUGIN_DST/bin/"
    ;;
  venv)
    echo "==> Bundling Python server into plugin/server/.venv ..."
    if [[ ! -x "$VENV_SRC/bin/obsidian-context-mcp" ]]; then
      echo "Creating dev venv at python/.venv ..."
      python3 -m venv "$VENV_SRC"
      "$VENV_SRC/bin/pip" install -q -e "$ROOT/python"
    fi
    mkdir -p "$PLUGIN_DST/server"
    rsync -a --delete \
      --exclude "__pycache__" \
      --exclude "*.pyc" \
      "$VENV_SRC/" "$PLUGIN_DST/server/.venv/"
    ;;
  skip)
    echo "==> Skipping server bundle (dev: set Python command in plugin settings)"
    ;;
  *)
    echo "Unknown BUNDLE_MODE=$BUNDLE_MODE" >&2
    exit 1
    ;;
esac

mkdir -p "$PLUGIN_DST/data"
echo ""
echo "Installed self-contained plugin → $PLUGIN_DST"
echo "  UI:     main.js"
echo "  Server: plugin/server/.venv or plugin/bin/"
echo "  Data:   plugin/data/ (index, scopes, models-cache, logs)"
echo ""
echo "Enable in Obsidian → Community plugins, then Restart server."
