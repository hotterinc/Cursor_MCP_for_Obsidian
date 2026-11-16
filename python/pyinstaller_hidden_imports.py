"""Eager imports so PyInstaller traces the embedding stack at build time."""

from __future__ import annotations

import huggingface_hub  # noqa: F401
import onnxruntime  # noqa: F401
import sentencepiece  # noqa: F401
