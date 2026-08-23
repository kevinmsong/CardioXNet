"""
CardioXNet desktop launcher.

Starts the FastAPI backend (uvicorn) on a free localhost port and opens the
server-rendered UI in a native window via pywebview. Works both in development
(`python launcher.py`) and when frozen by PyInstaller into a macOS ``.app`` or a
Windows ``.exe``.
"""
import sys
import os
import io
import threading
import time
import socket
import signal
from pathlib import Path

# PyInstaller windowed mode: sys.stdout/stderr are fake closed objects.
# Real writes raise "I/O operation on closed file". In frozen mode redirect to
# devnull; in dev mode keep the real (UTF-8) streams.
if getattr(sys, "frozen", False):
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
else:
    if sys.stdout and hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.stderr and hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Path / working-directory setup ──────────────────────────────────────────
if getattr(sys, "frozen", False):
    # Running as a PyInstaller bundle.
    # _MEIPASS holds the extracted Python modules + data - add to sys.path so
    # `import app...` resolves. Outputs are written next to the executable.
    BUNDLE_DIR = Path(sys._MEIPASS)
    sys.path.insert(0, str(BUNDLE_DIR))
    if sys.platform == "darwin" and ".app/Contents/MacOS" in sys.executable:
        # Inside a .app bundle, write outputs beside the .app, not deep in it.
        APP_DIR = Path(sys.executable).parents[3]
    else:
        APP_DIR = Path(sys.executable).parent
else:
    BUNDLE_DIR = Path(__file__).resolve().parent
    APP_DIR = Path(__file__).resolve().parent

os.chdir(APP_DIR)

# ── Log file next to the app so users can inspect failures ──────────────────
LOG_PATH = APP_DIR / "CardioXNet.log"
_log_fh = open(LOG_PATH, "w", encoding="utf-8", buffering=1)


def _log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass
    _log_fh.write(line + "\n")
    _log_fh.flush()


HOST = "127.0.0.1"
_START_ERROR = ""   # populated if the server thread crashes
_server = None      # uvicorn.Server instance


def _find_free_port() -> int:
    with socket.socket() as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def _wait_for_server(port: int, timeout: float = 120.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def _start_backend(port: int) -> None:
    """Run uvicorn in a daemon thread; capture startup exceptions to _START_ERROR."""
    global _server, _START_ERROR
    try:
        _log(f"Importing app  bundle={BUNDLE_DIR}  cwd={APP_DIR}")
        from app.main import app as fastapi_app  # noqa: F401
        _log("app.main imported OK")

        import uvicorn

        # FileHandler-based log config: uvicorn's default StreamHandler calls
        # sys.stderr.isatty() on the closed PyInstaller fake stream and crashes.
        log_cfg = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {"()": "logging.Formatter", "fmt": "%(levelname)s [%(name)s] %(message)s"},
                "access": {"()": "logging.Formatter", "fmt": "%(levelname)s [%(name)s] %(message)s"},
            },
            "handlers": {
                "default": {"class": "logging.FileHandler", "formatter": "default",
                            "filename": str(LOG_PATH), "mode": "a", "encoding": "utf-8"},
                "access": {"class": "logging.FileHandler", "formatter": "access",
                           "filename": str(LOG_PATH), "mode": "a", "encoding": "utf-8"},
            },
            "loggers": {
                "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
                "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
                "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
            },
            "root": {"handlers": ["default"], "level": "INFO"},
        }

        config = uvicorn.Config(fastapi_app, host=HOST, port=port, log_config=log_cfg, reload=False)
        _server = uvicorn.Server(config)
        _log(f"Starting uvicorn on {HOST}:{port}")
        _server.run()
        _log("uvicorn exited normally")
    except Exception:
        import traceback
        _START_ERROR = traceback.format_exc()
        _log(f"SERVER STARTUP FAILED:\n{_START_ERROR}")


def _shutdown() -> None:
    """Stop uvicorn and exit cleanly so no ports remain occupied."""
    global _server
    if _server is not None:
        _server.should_exit = True
    threading.Timer(2.5, lambda: os.kill(os.getpid(), signal.SIGTERM)).start()


def main() -> None:
    _log("CardioXNet launcher starting")
    _log(f"APP_DIR = {APP_DIR}")
    _log(f"BUNDLE  = {BUNDLE_DIR}")
    _log(f"Python  = {sys.version}")
    _log(f"Platform= {sys.platform}")

    import webview

    port = _find_free_port()
    _log(f"Allocated port {port}")

    threading.Thread(target=_start_backend, args=(port,), daemon=True).start()

    window = webview.create_window(
        "CardioXNet - Starting…",
        html="""
        <html><body style="margin:0;background:#0f766e;display:flex;flex-direction:column;
            align-items:center;justify-content:center;height:100vh;
            font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:white;">
          <div style="font-size:2.2rem;font-weight:800;letter-spacing:-1px;">CardioXNet</div>
          <div style="font-size:1rem;margin-top:8px;opacity:.8;">
            Cardiac Repair Pathway Discovery</div>
          <div style="margin-top:32px;font-size:.9rem;opacity:.65;">Starting server…</div>
        </body></html>
        """,
        width=520,
        height=320,
        resizable=True,
    )

    def _on_shown():
        if _wait_for_server(port, timeout=120):
            _log("Server ready - opening app")
            window.load_url(f"http://{HOST}:{port}")
            window.set_title("CardioXNet")
            window.resize(1820, 1170)
        else:
            detail = _START_ERROR or "(no traceback - check CardioXNet.log next to the app)"
            _log("Server did not respond in time")
            safe = detail.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            window.load_html(
                "<body style='font-family:monospace;padding:30px;background:#fff0f0;'>"
                "<h2 style='color:#c0392b'>CardioXNet failed to start</h2>"
                f"<p>Log: <b>{LOG_PATH}</b></p>"
                f"<pre style='font-size:.8rem;background:#eee;padding:12px;"
                f"overflow:auto;max-height:60vh'>{safe}</pre></body>"
            )

    window.events.shown += _on_shown

    webview.start(debug=False)   # blocks on the GUI main thread until the window closes
    _shutdown()


if __name__ == "__main__":
    main()
