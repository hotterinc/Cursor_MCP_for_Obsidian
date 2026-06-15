"""Eager imports so PyInstaller traces the embedding stack at build time."""

from __future__ import annotations

import safetensors  # noqa: F401
import sentence_transformers  # noqa: F401
import torch  # noqa: F401
import transformers  # noqa: F401
