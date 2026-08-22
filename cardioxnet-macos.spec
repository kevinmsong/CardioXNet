# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the CardioXNet macOS desktop app.

Build (must run ON macOS — PyInstaller does not cross-compile):
    pip install -r requirements.txt -r requirements-desktop.txt
    pyinstaller cardioxnet-macos.spec --clean --noconfirm

Output:
    dist/CardioXNet.app   ← double-clickable macOS application bundle
"""

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root = Path(SPECPATH)

# ── data files ───────────────────────────────────────────────────────────────
# The server-rendered UI lives entirely inside app/ (app/templates, app/static),
# so bundling the app package as plain data files covers the Jinja templates,
# CSS, and vendored JS. uvicorn imports `app.main` by object, not by path string,
# but app/main.py resolves templates/static relative to its own __file__, which
# lands inside _MEIPASS/app/* at runtime.
datas = [
    (str(root / "app"), "app"),
    (str(root / "config"), "config"),
    *collect_data_files("webview"),     # pywebview GUI resources
    *collect_data_files("reportlab"),   # PDF fonts
    *collect_data_files("jinja2"),
    *collect_data_files("sklearn"),
    *collect_data_files("pandas"),
    *collect_data_files("Bio"),         # BioPython data
    *collect_data_files("aiohttp"),
    *collect_data_files("groq"),
    *collect_data_files("scipy"),
    *collect_data_files("certifi"),     # TLS roots for HTTPS to GTEx/STRING/PubMed
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
    # web stack
    *collect_submodules("fastapi"),
    *collect_submodules("starlette"),
    *collect_submodules("pydantic"),
    *collect_submodules("pydantic_settings"),
    # app modules
    *collect_submodules("app"),
    # scientific stack
    *collect_submodules("networkx"),
    *collect_submodules("sklearn"),
    *collect_submodules("scipy"),
    *collect_submodules("numpy"),
    *collect_submodules("pandas"),
    *collect_submodules("Bio"),
    # async / HTTP
    *collect_submodules("aiohttp"),
    *collect_submodules("httpx"),
    *collect_submodules("requests"),
    "anyio", "anyio._backends._asyncio",
    "h11", "httptools", "websockets",
    # data / caching / retry
    *collect_submodules("diskcache"),
    *collect_submodules("tenacity"),
    # AI / reporting / templating
    *collect_submodules("groq"),
    *collect_submodules("reportlab"),
    *collect_submodules("jinja2"),
    # g:Profiler client (package name `gprofiler`)
    "gprofiler",
    # pywebview — Cocoa/WKWebView backend on macOS
    "webview", "webview.platforms.cocoa",
]

a = Analysis(
    [str(root / "launcher.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "seaborn", "IPython", "jupyter", "PyQt5", "PySide2"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CardioXNet",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                 # UPX is unreliable on macOS dylibs
    console=False,             # windowed — no terminal
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,          # host arch; set "universal2"/"arm64"/"x86_64" to pin
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="CardioXNet",
)

app = BUNDLE(
    coll,
    name="CardioXNet.app",
    icon=None,                 # set to "assets/CardioXNet.icns" to brand the app
    bundle_identifier="net.cardioxnet.desktop",
    info_plist={
        "CFBundleName": "CardioXNet",
        "CFBundleDisplayName": "CardioXNet",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "0.1.0",
        "NSHighResolutionCapable": True,
        # WKWebView talks to the local uvicorn server over plain HTTP on 127.0.0.1.
        "NSAppTransportSecurity": {"NSAllowsLocalNetworking": True},
        "LSMinimumSystemVersion": "11.0",
    },
)
