"""Unified single-command launcher for HANDVO Backend and Web Frontend."""

import os
import sys
import threading
import time
import webbrowser
import uvicorn


def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:8000")


def main():
    print("=" * 60)
    print("   ✋ HANDVO — AI Hand-Assisted AAC Communication System   ")
    print("   🌐 Starting Python Backend API & Web Frontend Server   ")
    print("   📍 URL: http://127.0.0.1:8000                          ")
    print("=" * 60)

    # Launch browser automatically
    threading.Thread(target=open_browser, daemon=True).start()

    # Run FastAPI server with Uvicorn
    uvicorn.run("backend.app.server:app", host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
