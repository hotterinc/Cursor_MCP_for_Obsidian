"""Entry point for python -m obsidian_context_mcp and PyInstaller sidecar binary."""

from __future__ import annotations

import multiprocessing
import sys


def _is_frozen_multiprocessing_reexec() -> bool:
    """PyInstaller onefile re-exec passes CPython flags (e.g. -B) to the same binary."""
    if not getattr(sys, "frozen", False) or len(sys.argv) < 2:
        return False
    first = sys.argv[1]
    return first.startswith("-") or first == "--multiprocessing-fork"


if __name__ == "__main__":
    multiprocessing.freeze_support()
    if _is_frozen_multiprocessing_reexec():
        # Worker/bootstrap process — not the vault-server CLI.
        raise SystemExit(0)
    from obsidian_context_mcp.cli.main import app

    app()
