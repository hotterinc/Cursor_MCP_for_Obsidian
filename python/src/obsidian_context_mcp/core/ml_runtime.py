"""Process-wide settings for PyTorch / HuggingFace on Windows."""

from __future__ import annotations

import os

_configured = False


def configure_ml_runtime() -> None:
    """Apply env defaults before importing torch or sentence-transformers."""
    global _configured
    if _configured:
        return
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    from obsidian_context_mcp.core.app_paths import get_shared_models_cache_dir

    cache = str(get_shared_models_cache_dir())
    os.environ.setdefault("HF_HOME", cache)
    os.environ.setdefault("HF_HUB_CACHE", cache)
    os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", cache)
    _configured = True
