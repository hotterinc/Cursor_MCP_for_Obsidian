"""Logging configuration — always stderr and log files, never stdout."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from obsidian_context_mcp.shared.constants import APP_NAME

_configured = False


def setup_logging(*, log_file: Path | None = None, level: str = "INFO") -> None:
    global _configured
    if _configured:
        return
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
        enqueue=True,
    )
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            level=level,
            rotation="10 MB",
            retention="7 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}",
            enqueue=True,
        )
    _configured = True


def get_logger():
    return logger.bind(app=APP_NAME)
