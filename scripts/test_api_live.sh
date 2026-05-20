#!/usr/bin/env bash
# Live smoke test against a running api.py server.
# Usage:
#   Terminal 1: make api
#   Terminal 2: make test-api
#   Or: API_URL=http://192.168.1.10:5000 make test-api

set -euo pipefail

API_URL="${API_URL:-http://127.0.0.1:5000}"
API_URL="${API_URL%/}"

echo "Testing API at $API_URL"

curl -sf "$API_URL/health" | grep -q '"status"' || {
  echo "FAIL: GET /health — is 'make api' running and reachable?" >&2
  exit 1
}
echo "OK: GET /health"

RESP=$(curl -sf -X POST "$API_URL/chat" \
  -H 'Content-Type: application/json' \
  -d '{"text":"hello"}')

echo "$RESP" | grep -q '"intent"' || {
  echo "FAIL: POST /chat missing intent field" >&2
  echo "$RESP" >&2
  exit 1
}
echo "$RESP" | grep -q '"reply"' || {
  echo "FAIL: POST /chat missing reply field" >&2
  exit 1
}
echo "OK: POST /chat (intent + reply present)"
echo "Sample reply (LLM may be offline):"
echo "$RESP" | head -c 400
echo ""
