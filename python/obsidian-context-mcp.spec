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

def _filter_cuda_binaries(entries: list) -> list:
    return [
        entry
        for entry in entries
        if not any(token in entry[0].lower() for token in block_torch_cuda)
    ]


def _filter_test_assets(entries: list) -> list:
    return [
        entry
        for entry in entries
        if "/test" not in entry[0].replace("\\", "/").lower()
        and "/tests/" not in entry[0].replace("\\", "/").lower()
    ]


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
    "torch",
    "sentence_transformers",
    "transformers",
    "safetensors",
    # CPU wheels ship these stubs; transformers/sentence-transformers import them.
    "torch.cuda",
    "torch.backends.cuda",
    "torch.distributed",
]

hiddenimports += collect_submodules("obsidian_context_mcp")
hiddenimports += collect_submodules("chromadb")

datas: list = []
binaries: list = []

# Keep collect_all narrow — broad collection blows past GitHub's 2 GiB release limit on Linux ARM.
for pkg in (
    "chromadb_rust_bindings",
    "tokenizers",
    "onnxruntime",
    "llama_cpp",
    "torch",
    "sentence_transformers",
    "transformers",
    "safetensors",
):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += _filter_test_assets(pkg_datas)
    binaries += _filter_cuda_binaries(pkg_binaries)
    hiddenimports += pkg_hidden

binaries += _filter_cuda_binaries(collect_dynamic_libs("numpy"))
binaries += _filter_cuda_binaries(collect_dynamic_libs("llama_cpp"))
binaries += _filter_cuda_binaries(collect_dynamic_libs("torch"))

binaries = _filter_cuda_binaries(binaries)
datas = _filter_test_assets(datas)

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
    "torch.backends.cudnn",
    "torchvision",
    "torchaudio",
]

a = Analysis(
    ["src/obsidian_context_mcp/__main__.py", "pyinstaller_hidden_imports.py"],
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
