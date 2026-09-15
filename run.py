"""Unified single-command launcher for HANDVO Backend and Web Frontend."""

import os
import sys
import threading
import time
import webbrowser
import uvicorn

# Force UTF-8 stdout encoding on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


import socket

def find_free_port(preferred_port=8000):
    """Check if preferred_port is available, otherwise find the next free port."""
    for port in range(preferred_port, preferred_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return preferred_port


def open_browser(port):
    time.sleep(1.2)
    webbrowser.open(f"http://127.0.0.1:{port}")


def main():
    port = find_free_port(8000)
    print("=" * 60)
    print("   HANDVO - AI Hand-Assisted AAC Communication System   ")
    print("   Starting Python Backend API & Web Frontend Server    ")
    print(f"   URL: http://127.0.0.1:{port}                        ")
    print("=" * 60)

    # Launch browser automatically
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    # Run FastAPI server with Uvicorn
    uvicorn.run("backend.app.server:app", host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
