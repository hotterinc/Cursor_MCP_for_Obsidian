"""PyInstaller runtime hooks for the frozen sidecar."""

from __future__ import annotations

import os
import sys


def _bootstrap_cpu_torch() -> None:
    if not getattr(sys, "frozen", False):
        return
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def _bootstrap_llama_cpp_lib_path() -> None:
    if not getattr(sys, "frozen", False):
        return
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return
    lib_dir = os.path.join(meipass, "llama_cpp", "lib")
    if os.path.isdir(lib_dir):
        os.environ.setdefault("LLAMA_CPP_LIB_PATH", lib_dir)


_bootstrap_cpu_torch()
_bootstrap_llama_cpp_lib_path()
