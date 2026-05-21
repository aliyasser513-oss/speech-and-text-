#!/usr/bin/env python3
"""Run API + Expo together (cross-platform). Ctrl+C stops both."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOBILE = ROOT / "mobile"


def venv_python() -> Path:
    if sys.platform == "win32":
        return ROOT / ".venv" / "Scripts" / "python.exe"
    return ROOT / ".venv" / "bin" / "python"


def main() -> None:
    py = venv_python()
    if not py.is_file():
        print("Run 'make install-python' first.", file=sys.stderr)
        sys.exit(1)

    npx = "npx.cmd" if sys.platform == "win32" else "npx"

    print("Starting API (http://0.0.0.0:5000) and Expo (LAN) …")
    print("Phone: Expo Go → scan QR. LAN IP written to mobile/.env before Expo.")
    print("Press Ctrl+C to stop both.\n")

    subprocess.run([str(py), str(ROOT / "scripts" / "write_mobile_env.py")], cwd=ROOT, check=False)
    api = subprocess.Popen([str(py), str(ROOT / "api.py")], cwd=ROOT)
    expo = subprocess.Popen(
        [npx, "expo", "start", "--lan"],
        cwd=MOBILE,
        shell=(sys.platform == "win32"),
    )

    try:
        while True:
            if api.poll() is not None:
                print("API process exited.", file=sys.stderr)
                break
            if expo.poll() is not None:
                print("Expo process exited.", file=sys.stderr)
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping …")
    finally:
        for proc in (api, expo):
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()


if __name__ == "__main__":
    main()
