#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/python"
uv sync --all-extras
uv run obsidian-context-mcp server --project-root "${1:-$ROOT}"
