# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Obsidian plugin sidecar (vault-server)."""

from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs, collect_submodules

block_torch_cuda = (
    "cuda",
    "cudnn",
    "nvidia",
    "cublas",
    "cusparse",
    "nccl",
    "cufft",
    "curand",
    "cusolver",
)

hiddenimports = [
    "obsidian_context_mcp",
    "uvicorn",
    "starlette.routing",
    "mcp.server.sse",
    "chromadb.telemetry.product.posthog",
    "chromadb.api.rust",
    "chromadb_rust_bindings",
    "numpy.linalg._umath_linalg",
    "numpy.core._multiarray_umath",
    "llama_cpp",
    # CPU wheels still ship torch.cuda stubs; sentence-transformers imports them.
    "torch.cuda",
    "torch.backends.cuda",
]

hiddenimports += collect_submodules("obsidian_context_mcp")
hiddenimports += collect_submodules("chromadb")

datas: list = []
binaries: list = []

# Keep collect_all narrow — broad collection blows past GitHub's 2 GiB release limit on Linux ARM.
for pkg in ("chromadb_rust_bindings", "tokenizers", "onnxruntime", "llama_cpp"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

binaries += collect_dynamic_libs("numpy")
binaries += collect_dynamic_libs("llama_cpp")

binaries = [
    entry
    for entry in binaries
    if not any(token in entry[0].lower() for token in block_torch_cuda)
]
datas = [
    entry
    for entry in datas
    if "/test" not in entry[0].replace("\\", "/").lower()
    and "/tests/" not in entry[0].replace("\\", "/").lower()
]

excludes = [
    "tkinter",
    "matplotlib",
    "IPython",
    "jupyter",
    "notebook",
    "pandas",
    "tensorflow",
    "jax",
    "pytest",
    "unittest",
    "torch.distributed",
    "torch.testing",
    "torch.backends.cudnn",
    "torchvision",
    "torchaudio",
]

a = Analysis(
    ["src/obsidian_context_mcp/__main__.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["pyinstaller_runtime_llama.py"],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="obsidian-context-mcp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
