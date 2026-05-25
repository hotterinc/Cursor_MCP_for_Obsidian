#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$ROOT/scripts/build-python.sh"
cd "$ROOT/apps/desktop"
pnpm install
pnpm build
pnpm package
