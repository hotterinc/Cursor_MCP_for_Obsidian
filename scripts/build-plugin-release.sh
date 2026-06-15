#!/usr/bin/env bash
# Build a drop-in Obsidian plugin zip for GitHub releases.
#
# Contents (no vault data / index / scopes):
#   obsidian-context-mcp/
#     manifest.json, main.js, styles.css
#     bin/obsidian-context-mcp     — standalone vault-server (PyInstaller)
#     INSTALL.md
#
# Usage:
#   ./scripts/build-plugin-release.sh
#   VERSION=0.1.0 ./scripts/build-plugin-release.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN_SRC="$ROOT/obsidian-plugin"
VERSION="${VERSION:-$(python3 -c "import json; print(json.load(open('$PLUGIN_SRC/manifest.json'))['version'])")}"
DIST="$ROOT/dist/release"
STAGE="$DIST/obsidian-context-mcp"
ARCH="$(uname -m)"
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ZIP_NAME="obsidian-context-mcp-${VERSION}-${OS}-${ARCH}.zip"
ZIP_PATH="$DIST/$ZIP_NAME"

echo "==> Building plugin UI..."
cd "$PLUGIN_SRC"
npm install
npm run build

echo "==> Building standalone vault-server binary..."
bash "$ROOT/scripts/build-plugin-sidecar.sh"

echo "==> Staging release (no index / scopes / models / logs)..."
rm -rf "$STAGE"
mkdir -p "$STAGE/bin"

install -m 644 "$PLUGIN_SRC/manifest.json" "$STAGE/"
install -m 644 "$PLUGIN_SRC/main.js" "$STAGE/"
install -m 644 "$PLUGIN_SRC/styles.css" "$STAGE/"

if [[ -f "$PLUGIN_SRC/bin/obsidian-context-mcp.exe" ]]; then
  install -m 755 "$PLUGIN_SRC/bin/obsidian-context-mcp.exe" "$STAGE/bin/"
  PLATFORM_NOTE="Первый запуск на Windows: если SmartScreen блокирует \`obsidian-context-mcp.exe\`, нажмите «Подробнее» → «Выполнить в любом случае»."
elif [[ -f "$PLUGIN_SRC/bin/obsidian-context-mcp" ]]; then
  install -m 755 "$PLUGIN_SRC/bin/obsidian-context-mcp" "$STAGE/bin/"
  PLATFORM_NOTE="Первый запуск на macOS: если vault-server не стартует, в Terminal выполните:
\`xattr -dr com.apple.quarantine \"ВашVault/.obsidian/plugins/obsidian-context-mcp\"\`"
else
  echo "Sidecar binary not found in $PLUGIN_SRC/bin/" >&2
  exit 1
fi

cat > "$STAGE/INSTALL.md" <<EOF
# Obsidian Context MCP — установка

1. Распакуйте архив.
2. Скопируйте папку \`obsidian-context-mcp\` в:
   \`ВашVault/.obsidian/plugins/\`
3. Obsidian → Settings → Community plugins → включите **Obsidian Context MCP**.
4. Settings плагина → **Access scopes** → создайте scope → **Copy JSON** → вставьте в Cursor \`.cursor/mcp.json\`.

${PLATFORM_NOTE}

Папка \`data/\` (индекс, scopes, логи) создаётся автоматически при первом запуске — в архиве её нет намеренно.

Платформа сборки: ${OS}-${ARCH}
Версия: ${VERSION}
EOF

echo "==> Creating zip..."
mkdir -p "$DIST"
rm -f "$ZIP_PATH"
(
  cd "$DIST"
  zip -r -q "$ZIP_NAME" obsidian-context-mcp \
    -x "*.DS_Store" \
    -x "*__pycache__*" \
    -x "*.pyc"
)

echo ""
echo "Release zip: $ZIP_PATH ($(du -h "$ZIP_PATH" | cut -f1))"
echo "Contents:"
find "$STAGE" -type f | sed "s|$STAGE/|  |"
