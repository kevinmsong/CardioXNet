"""
CardioXNet Desktop Launcher
Starts the FastAPI backend and opens the app in a native window via pywebview.
"""
import sys
import os
import io
import threading
import time
import socket
import logging
import signal
from pathlib import Path

# PyInstaller windowed mode: sys.stdout/stderr are fake closed objects.
# Empty writes may succeed but real writes raise "I/O operation on closed file".
# In frozen mode always redirect to devnull; in dev mode keep the real streams.
if getattr(sys, 'frozen', False):
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')
else:
    # Dev mode: ensure UTF-8 encoding
    if sys.stdout and hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'buffer'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ── Path / working-directory setup ──────────────────────────────────────────
if getattr(sys, 'frozen', False):
    # Running as a PyInstaller exe
    # _MEIPASS holds extracted Python modules — add to sys.path for imports only
    BUNDLE_DIR = Path(sys._MEIPASS)
    sys.path.insert(0, str(BUNDLE_DIR))
    # Working directory = folder containing the .exe (writable; outputs saved here)
    APP_DIR = Path(sys.executable).parent
else:
    BUNDLE_DIR = Path(__file__).parent
    APP_DIR = Path(__file__).parent

os.chdir(APP_DIR)

# ── Log file next to the exe so the user can inspect failures ───────────────
LOG_PATH = APP_DIR / "CardioXNet.log"
_log_fh = open(LOG_PATH, "w", encoding="utf-8", buffering=1)


def _log(msg: str):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass
    _log_fh.write(line + "\n")
    _log_fh.flush()


HOST = "127.0.0.1"
_START_ERROR: str = ""   # populated if the server thread crashes


def _find_free_port() -> int:
    with socket.socket() as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def _wait_for_server(port: int, timeout: float = 90.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


_server = None   # uvicorn.Server instance


def _start_backend(port: int):
    """Run uvicorn in a daemon thread; capture any startup exception to _START_ERROR."""
    global _server, _START_ERROR
    try:
        _log(f"Importing app  bundle={BUNDLE_DIR}  cwd={APP_DIR}")

        # Import the FastAPI app object directly — any module-level import
        # error surfaces here with a full traceback instead of being swallowed
        # by uvicorn's logging reset.
        _log("Importing app.main …")
        from app.main import app as fastapi_app  # noqa: F401
        _log("app.main imported OK")

        import uvicorn

        # Custom log config using FileHandler — avoids the windowed-mode crash
        # where uvicorn's default StreamHandler calls sys.stderr.isatty() on a
        # closed PyInstaller fake stream (ValueError: I/O operation on closed file).
        log_cfg = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": "logging.Formatter",
                    "fmt": "%(levelname)s [%(name)s] %(message)s",
                },
                "access": {
                    "()": "logging.Formatter",
                    "fmt": "%(levelname)s [%(name)s] %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "class": "logging.FileHandler",
                    "formatter": "default",
                    "filename": str(LOG_PATH),
                    "mode": "a",
                    "encoding": "utf-8",
                },
                "access": {
                    "class": "logging.FileHandler",
                    "formatter": "access",
                    "filename": str(LOG_PATH),
                    "mode": "a",
                    "encoding": "utf-8",
                },
            },
            "loggers": {
                "uvicorn":        {"handlers": ["default"], "level": "DEBUG", "propagate": False},
                "uvicorn.error":  {"handlers": ["default"], "level": "DEBUG", "propagate": False},
                "uvicorn.access": {"handlers": ["access"],  "level": "DEBUG", "propagate": False},
            },
            # Root logger captures app/fastapi/service startup errors too
            "root": {"handlers": ["default"], "level": "INFO"},
        }

        config = uvicorn.Config(
            fastapi_app,
            host=HOST,
            port=port,
            log_config=log_cfg,
            reload=False,
        )
        _server = uvicorn.Server(config)
        _log(f"Starting uvicorn on {HOST}:{port}")
        _server.run()
        _log("uvicorn exited normally")
    except Exception:
        import traceback
        _START_ERROR = traceback.format_exc()
        _log(f"SERVER STARTUP FAILED:\n{_START_ERROR}")


def _shutdown():
    """Stop uvicorn and exit cleanly so no ports remain occupied."""
    global _server
    if _server is not None:
        _server.should_exit = True
    threading.Timer(2.5, lambda: os.kill(os.getpid(), signal.SIGTERM)).start()


def main():
    _log("CardioXNet launcher starting")
    _log(f"APP_DIR  = {APP_DIR}")
    _log(f"BUNDLE   = {BUNDLE_DIR}")
    _log(f"Python   = {sys.version}")

    import webview

    port = _find_free_port()
    _log(f"Allocated port {port}")

    t = threading.Thread(target=_start_backend, args=(port,), daemon=True)
    t.start()

    splash = webview.create_window(
        "CardioXNet — Starting…",
        html="""
        <html><body style="margin:0;background:#1E6B52;display:flex;flex-direction:column;
            align-items:center;justify-content:center;height:100vh;
            font-family:sans-serif;color:white;">
          <div style="font-size:2.2rem;font-weight:800;letter-spacing:-1px;">CardioXNet</div>
          <div style="font-size:1rem;margin-top:8px;opacity:.75;">
            Cardiovascular Disease Pathway Discovery</div>
          <div style="margin-top:32px;font-size:.9rem;opacity:.6;">Starting server…</div>
        </body></html>
        """,
        width=520,
        height=320,
        resizable=True,
    )

    def _on_shown():
        ready = _wait_for_server(port, timeout=90)
        if ready:
            _log(f"Server ready — opening app")
            splash.load_url(f"http://{HOST}:{port}")
            splash.set_title("CardioXNet")
            splash.resize(1820, 1170)
        else:
            detail = _START_ERROR or "(no traceback — check CardioXNet.log next to the exe)"
            _log(f"Server did not respond after 90s")
            safe = detail.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            splash.load_html(
                "<body style='font-family:monospace;padding:30px;background:#fff0f0;'>"
                "<h2 style='color:#c0392b'>CardioXNet failed to start</h2>"
                f"<p>Log: <b>{LOG_PATH}</b></p>"
                f"<pre style='font-size:.8rem;background:#eee;padding:12px;"
                f"overflow:auto;max-height:60vh'>{safe}</pre>"
                "</body>"
            )

    splash.events.shown += _on_shown

    webview.start(debug=False)
    _shutdown()


if __name__ == "__main__":
    main()
