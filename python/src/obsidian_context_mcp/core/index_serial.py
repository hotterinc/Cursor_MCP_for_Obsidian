"""Serialize vault indexing — one embed/index operation at a time."""

from __future__ import annotations

import threading

INDEX_SERIAL_LOCK = threading.RLock()
