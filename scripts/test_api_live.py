#!/usr/bin/env python3
"""Live smoke test against a running api.py server (cross-platform)."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API_URL = os.environ.get("API_URL", "http://127.0.0.1:5000").rstrip("/")


def get(path: str) -> bytes:
    req = urllib.request.Request(f"{API_URL}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def post_json(path: str, body: dict) -> bytes:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{API_URL}{path}",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def main() -> None:
    print(f"Testing API at {API_URL}")

    try:
        health = json.loads(get("/health"))
    except urllib.error.URLError as exc:
        print(f"FAIL: GET /health — is 'make api' running? {exc}", file=sys.stderr)
        sys.exit(1)

    if health.get("status") != "ok":
        print(f"FAIL: unexpected /health payload: {health}", file=sys.stderr)
        sys.exit(1)
    print("OK: GET /health")

    try:
        chat = json.loads(post_json("/chat", {"text": "hello"}))
    except urllib.error.URLError as exc:
        print(f"FAIL: POST /chat — {exc}", file=sys.stderr)
        sys.exit(1)

    for key in ("intent", "reply"):
        if key not in chat:
            print(f"FAIL: POST /chat missing {key!r}: {chat}", file=sys.stderr)
            sys.exit(1)

    print("OK: POST /chat (intent + reply present)")
    print("Sample reply (LLM may be offline):")
    sample = json.dumps(chat, ensure_ascii=False)[:400]
    print(sample)
    if len(sample) >= 400:
        print("...")


if __name__ == "__main__":
    main()
