"""
start.py
Resilient uvicorn launcher. Auto-restarts if the server crashes.
Use this instead of running uvicorn directly.
Run with: python start.py
"""
# BEFORE editing this file: cd backend && python check.py
# AFTER editing this file:  cd backend && python check.py
# If check.py fails after your edit, revert the change immediately.

import subprocess
import time
import sys

MAX_RESTARTS = 10
RESTART_DELAY = 3  # seconds between restarts


def run():
    restarts = 0
    while restarts < MAX_RESTARTS:
        print(f"\n[start.py] Starting uvicorn (attempt {restarts + 1})...")
        result = subprocess.run([
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--reload",
            "--port", "8000",
            "--reload-delay", "1",
            "--timeout-keep-alive", "120",
        ])
        if result.returncode == 0:
            print("[start.py] Uvicorn exited cleanly.")
            break
        restarts += 1
        print(f"[start.py] Crashed (code {result.returncode}). "
              f"Restarting in {RESTART_DELAY}s...")
        time.sleep(RESTART_DELAY)
    else:
        print("[start.py] Too many crashes. Check your code and restart manually.")


if __name__ == "__main__":
    run()
