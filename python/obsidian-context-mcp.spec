# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Obsidian plugin sidecar (vault-server)."""

from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs, collect_submodules

hiddenimports = [
    "obsidian_context_mcp",
    "uvicorn",
    "starlette.routing",
    "mcp.server.sse",
    # chromadb telemetry (lazy-imported, easy to miss)
    "chromadb.telemetry.product.posthog",
    # numpy compiled extensions (fixes _umath_linalg import in onefile bundles)
    "numpy.linalg._umath_linalg",
    "numpy.core._multiarray_umath",
]

hiddenimports += collect_submodules("obsidian_context_mcp")
hiddenimports += collect_submodules("chromadb")

datas: list = []
binaries: list = []

for pkg in ("numpy", "chromadb", "sentence_transformers", "sklearn", "onnxruntime", "tokenizers"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

binaries += collect_dynamic_libs("numpy")

a = Analysis(
    ["src/obsidian_context_mcp/__main__.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
