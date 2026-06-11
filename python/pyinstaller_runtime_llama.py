"""PyInstaller runtime: point llama_cpp at bundled native libs in _MEIPASS."""

from __future__ import annotations

import os
import sys


def _bootstrap_llama_cpp_lib_path() -> None:
    if not getattr(sys, "frozen", False):
        return
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return
    lib_dir = os.path.join(meipass, "llama_cpp", "lib")
    if os.path.isdir(lib_dir):
        os.environ.setdefault("LLAMA_CPP_LIB_PATH", lib_dir)


_bootstrap_llama_cpp_lib_path()
