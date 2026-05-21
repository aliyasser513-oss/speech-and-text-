#!/usr/bin/env python3
"""Remove __pycache__ directories (cross-platform)."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for path in ROOT.rglob("__pycache__"):
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
        print(f"removed {path}")
