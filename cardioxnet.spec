# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for CardioXNet desktop app.
Run:  pyinstaller cardioxnet.spec
Output: dist/CardioXNet.exe  (single-file, windowed)
"""

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root = Path(SPECPATH)
frontend_dist = root / "frontend" / "dist"

# ── data files ──────────────────────────────────────────────────────────────
datas = [
    # app source — included as plain files so uvicorn's string import works
    (str(root / "app"), "app"),
    # pre-built React frontend
    (str(frontend_dist), "frontend_dist"),
    # app config
    (str(root / "config"), "config"),
    # pywebview GUI resources
    *collect_data_files("webview"),
    # scientific / ML data files (fonts, encoders, lookup tables, etc.)
    *collect_data_files("reportlab"),   # PDF fonts
    *collect_data_files("jinja2"),      # template resources
    *collect_data_files("sklearn"),     # sklearn data
    *collect_data_files("pandas"),      # pandas data
    *collect_data_files("Bio"),         # BioPython data
    *collect_data_files("aiohttp"),     # aiohttp mime data
    *collect_data_files("groq"),        # groq client resources
    *collect_data_files("scipy"),       # scipy data files
]

# ── hidden imports ───────────────────────────────────────────────────────────
hiddenimports = [
    # uvicorn internals
    "uvicorn.logging",
    "uvicorn.loops", "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets", "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan", "uvicorn.lifespan.on",
    # fastapi / starlette / pydantic
    *collect_submodules("fastapi"),
    *collect_submodules("starlette"),
    *collect_submodules("pydantic"),
    *collect_submodules("pydantic_settings"),
    # app modules
    *collect_submodules("app"),
    # scientific stack — full submodule collection
    *collect_submodules("networkx"),
    *collect_submodules("sklearn"),
    *collect_submodules("scipy"),
    *collect_submodules("numpy"),
    *collect_submodules("pandas"),
    # bioinformatics
    *collect_submodules("Bio"),
    # async / HTTP
    *collect_submodules("aiohttp"),
    *collect_submodules("httpx"),
    *collect_submodules("requests"),
    "anyio", "anyio._backends._asyncio",
    "h11", "httptools", "watchfiles", "websockets",
    # data / caching
    *collect_submodules("diskcache"),
    *collect_submodules("tenacity"),
    # AI / report
    *collect_submodules("groq"),
    *collect_submodules("reportlab"),
    *collect_submodules("jinja2"),
    # g:Profiler
    "gprofiler",
    # pywebview
    "webview", "webview.platforms.winforms",
]

# ── analysis ─────────────────────────────────────────────────────────────────
a = Analysis(
    [str(root / "launcher.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "IPython", "jupyter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="CardioXNet",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # windowed — no terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,           # add .ico path here to set a custom icon
)
