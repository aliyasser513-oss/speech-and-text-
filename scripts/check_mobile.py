#!/usr/bin/env python3
"""Fast mobile layout checks (cross-platform)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOBILE = ROOT / "mobile"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def main() -> None:
    pkg_path = MOBILE / "package.json"
    if not pkg_path.is_file():
        fail("missing mobile/package.json")

    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    if pkg.get("main") != "node_modules/expo/AppEntry.js":
        fail("package.json main must be node_modules/expo/AppEntry.js")
    if "expo-constants" not in pkg.get("dependencies", {}):
        fail("expo-constants must be in mobile/package.json dependencies")

    app_js = MOBILE / "App.js"
    if not app_js.is_file():
        fail("missing mobile/App.js")
    if "devApiBase" not in app_js.read_text(encoding="utf-8"):
        fail("App.js must define devApiBase() for LAN API auto-detect")

    icon = MOBILE / "assets" / "icon.png"
    if not icon.is_file() or icon.stat().st_size == 0:
        fail("missing mobile/assets/icon.png")

    ok("mobile layout and Expo entry configuration")


if __name__ == "__main__":
    main()
