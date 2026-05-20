"""Static checks for Expo mobile project layout."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOBILE = ROOT / "mobile"


def test_package_json_entry_point():
    pkg = json.loads((MOBILE / "package.json").read_text())
    assert pkg["main"] == "node_modules/expo/AppEntry.js"


def test_expo_constants_dependency():
    pkg = json.loads((MOBILE / "package.json").read_text())
    assert "expo-constants" in pkg.get("dependencies", {})


def test_app_js_exists():
    assert (MOBILE / "App.js").is_file()


def test_assets_icon_exists():
    icon = MOBILE / "assets" / "icon.png"
    assert icon.is_file()
    assert icon.stat().st_size > 0


def test_app_json_icon_path():
    app = json.loads((MOBILE / "app.json").read_text())
    icon_rel = app["expo"]["icon"]
    assert (MOBILE / icon_rel).is_file()
