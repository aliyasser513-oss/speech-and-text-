#!/usr/bin/env bash
# Fast mobile layout checks (no Metro / Expo runtime).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MOBILE="$ROOT/mobile"

fail() { echo "FAIL: $*" >&2; exit 1; }
ok()   { echo "OK: $*"; }

[[ -f "$MOBILE/package.json" ]] || fail "missing mobile/package.json"
grep -q 'node_modules/expo/AppEntry.js' "$MOBILE/package.json" \
  || fail 'package.json main must be node_modules/expo/AppEntry.js'

[[ -f "$MOBILE/App.js" ]] || fail "missing mobile/App.js"
[[ -f "$MOBILE/assets/icon.png" ]] || fail "missing mobile/assets/icon.png"

grep -q 'expo-constants' "$MOBILE/package.json" \
  || fail "expo-constants must be in mobile/package.json dependencies"

grep -q 'devApiBase' "$MOBILE/App.js" \
  || fail "App.js must define devApiBase() for LAN API auto-detect"

ok "mobile layout and Expo entry configuration"
