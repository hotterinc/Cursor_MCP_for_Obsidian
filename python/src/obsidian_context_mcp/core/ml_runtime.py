"""Process-wide settings for the ONNX / HuggingFace embedding runtime."""

from __future__ import annotations

import os
from pathlib import Path

_configured = False


def configure_ml_runtime(*, data_dir: Path | None = None) -> None:
    """Apply env defaults before importing onnxruntime or tokenizers."""
    global _configured
    if _configured:
        return
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    if data_dir is not None:
        from obsidian_context_mcp.core.vault_paths import get_vault_models_cache_dir

        cache = str(get_vault_models_cache_dir(data_dir))
    else:
        from obsidian_context_mcp.core.app_paths import get_shared_models_cache_dir

        cache = str(get_shared_models_cache_dir())
    os.environ.setdefault("HF_HOME", cache)
    os.environ.setdefault("HF_HUB_CACHE", cache)
    _configured = True
