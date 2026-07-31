"""
yfWatchlist desktop launcher.

Wraps the FastHTML app from main.py in a native OS window via pywebview,
so it runs as a standalone desktop app instead of a browser tab.

  - Spawns uvicorn (reload OFF) in a daemon thread.
  - Waits for the port to accept connections.
  - Opens a 1280×800 native window pointed at the local server.
  - Closing the window shuts the server down (daemon thread dies with main).

Usage:
    python app_desktop.py

Requires (already installed):
    pywebview, uvicorn, fasthtml, yfinance, pandas, numpy
"""
from __future__ import annotations

import sys
import json
import importlib.util
import socket
import threading
import time
from pathlib import Path

import uvicorn
import webview

HOST = "127.0.0.1"
PORT = 5012  # dedicated port to avoid colliding with python main.py on 5001
DEFAULT_W, DEFAULT_H = 1280, 800
TITLE = "yfWatchlist — Global Watchlist Manager"
READY_TIMEOUT = 30.0  # seconds to wait for server bind

# Resolve base dir both for `python app_desktop.py` and frozen .exe (PyInstaller).
# Frozen: sys.executable = path to .exe → write state next to it.
# Source: __file__ = path to .py → write state next to source. Same behavior as before.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

# Persisted window geometry (saved on every resize/move + on close).
STATE_FILE = BASE_DIR / "_desktop_state.json"
_geom_lock = threading.Lock()

def import_app():
    """Import main.py as a module (so its module-level storage/app build runs)
    and return the FastHTML `app` object. Does NOT execute the __main__ guard,
    so no second uvicorn is spawned."""
    # PyInstaller bundles main.py into the exe; spec_from_file_location can't load it.
    # In frozen mode, rely on the bundled module instead.
    if getattr(sys, "frozen", False):
        import main  # noqa: F401  -- bundled by PyInstaller
        return main.app
    spec = importlib.util.spec_from_file_location("main", str(BASE_DIR / "main.py"))
    main = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main)
    return main.app


def wait_for_port(host: str, port: int, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.15)
    return False


def load_geometry() -> dict:
    """Return saved window geometry {w,h,x,y} or sensible defaults."""
    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            g = json.load(f) or {}
        w = int(g.get("w") or DEFAULT_W)
        h = int(g.get("h") or DEFAULT_H)
        # x/y are optional (first launch or moved-off-screen): caller lets
        # the OS place the window if either is None.
        x = g.get("x")
        y = g.get("y")
        x = int(x) if isinstance(x, int) else None
        y = int(y) if isinstance(y, int) else None
        return {"w": w, "h": h, "x": x, "y": y}
    except (OSError, ValueError, json.JSONDecodeError):
        return {"w": DEFAULT_W, "h": DEFAULT_H, "x": None, "y": None}


def save_geometry(w: int, h: int, x: int | None = None, y: int | None = None) -> None:
    """Persist window size+position to disk (best-effort)."""
    with _geom_lock:
        try:
            with STATE_FILE.open("w", encoding="utf-8") as f:
                json.dump({"w": int(w), "h": int(h), "x": x, "y": y}, f)
        except OSError:
            pass


def _on_resized(window, w=None, h=None):
    """pywebview passes (width, height) on resize; (x, y) on move."""
    try:
        if w is not None and h is not None:
            # Don't block the UI thread: read x/y from the live window.
            try:
                x = window.x
                y = window.y
            except Exception:
                x = y = None
            save_geometry(w, h, x, y)
    except Exception:
        pass


def _on_moved(window, x=None, y=None):
    try:
        if x is not None and y is not None:
            save_geometry(window.width, window.height, x, y)
    except Exception:
        pass


def start_server(app, ready_event: threading.Event):
    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    # Signal main thread as soon as the loop is ready-ish.
    def _kick():
        while not server.started:
            time.sleep(0.1)
        ready_event.set()
    threading.Thread(target=_kick, daemon=True).start()
    server.run()


def main():
    print("=" * 56)
    print("  yfWatchlist — desktop launcher (pywebview + FastHTML)")
    print("=" * 56)
    app = import_app()

    ready = threading.Event()
    server_thread = threading.Thread(
        target=start_server, args=(app, ready), daemon=True
    )
    server_thread.start()

    # Belt + suspenders: either uvicorn's `started` flag OR raw socket probe.
    if not ready.wait(READY_TIMEOUT):
        if not wait_for_port(HOST, PORT, 5.0):
            print("ERROR: server did not bind in time; aborting window open.")
            return
    url = f"http://{HOST}:{PORT}/"
    geo = load_geometry()
    print(f"  Server up at {url} — opening native window {geo['w']}x{geo['h']}…")

    win = webview.create_window(
        TITLE,
        url,
        width=geo["w"],
        height=geo["h"],
        x=geo["x"],
        y=geo["y"],
        min_size=(760, 480),
        text_select=True,
    )
    # Persist size + position whenever the user changes them.
    win.events.resized += _on_resized
    win.events.moved   += _on_moved

    # Blocks until the window is closed. Returns control → daemon server dies.
    webview.start()

    # Final fallback in case the very last resize/move event didn't fire:
    # read straight from the window object (props block until shown, then
    # still return the last-known values even after close in pywebview).
    try:
        save_geometry(win.width, win.height, win.x, win.y)
    except Exception:
        pass
    print("  Window closed. Done.")


if __name__ == "__main__":
    main()
