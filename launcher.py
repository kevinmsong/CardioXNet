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

# Fix stdout encoding on Windows
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# When frozen by PyInstaller, add the bundle dir to sys.path
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    sys.path.insert(0, bundle_dir)
    # Set working directory to bundle so relative paths resolve
    os.chdir(bundle_dir)

HOST = "127.0.0.1"
PORT = 8765  # Use a fixed internal port, away from dev 8000


def _find_free_port():
    with socket.socket() as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def _wait_for_server(port: int, timeout: float = 30.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.15)
    return False


def _start_backend(port: int):
    """Run uvicorn in the current thread (called from a daemon thread)."""
    import uvicorn
    # Suppress noisy startup logs in windowed mode
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=port,
        log_level="warning",
        reload=False,
    )


def main():
    import webview

    port = _find_free_port()
    url = f"http://{HOST}:{port}"

    # Start backend in background daemon thread
    t = threading.Thread(target=_start_backend, args=(port,), daemon=True)
    t.start()

    # Show a splash while the server warms up
    splash = webview.create_window(
        "CardioXNet — Starting…",
        html="""
        <html><body style="margin:0;background:#1E6B52;display:flex;flex-direction:column;
            align-items:center;justify-content:center;height:100vh;font-family:sans-serif;color:white;">
          <div style="font-size:2.2rem;font-weight:800;letter-spacing:-1px;">CardioXNet</div>
          <div style="font-size:1rem;margin-top:8px;opacity:.75;">Cardiovascular Disease Pathway Discovery</div>
          <div style="margin-top:32px;font-size:.9rem;opacity:.6;">Starting server…</div>
        </body></html>
        """,
        width=520,
        height=320,
        resizable=True,
    )

    def _on_shown():
        ready = _wait_for_server(port, timeout=45)
        if ready:
            splash.load_url(url)
            splash.set_title("CardioXNet")
            splash.resize(1820, 1170)
        else:
            splash.load_html(
                "<body style='font-family:sans-serif;padding:40px;color:#c0392b;'>"
                "<h2>Failed to start the CardioXNet server.</h2>"
                "<p>Please check that port is not in use and try again.</p>"
                "</body>"
            )

    splash.events.shown += _on_shown

    webview.start(debug=False)


if __name__ == "__main__":
    main()
