"""
MLPMP Full Suite v2.0.4 - Main Launcher Entrypoint.
Starts the local WebGUI server and opens the browser interface.
"""

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))

from server.app import run_server, ensure_assets


def open_browser(port: int):
    time.sleep(1.0)
    webbrowser.open(f"http://127.0.0.1:{port}/")


def main():
    port = 8080
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])

    print("==================================================")
    print("  MLPMP FULL SUITE v2.0.4 // LIVE RAM ARCHITECTURE")
    print("==================================================")
    print("Target Process: MyLittlePony_x64.exe (v11.4.1a)")
    print(f"Web Interface:  http://127.0.0.1:{port}/")
    print("Press Ctrl+C to stop the Suite.\n")

    ensure_assets(PROJECT_DIR)

    t = threading.Thread(target=open_browser, args=(port,), daemon=True)
    t.start()

    run_server(port)


if __name__ == "__main__":
    main()
