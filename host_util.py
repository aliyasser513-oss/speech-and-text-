"""Small network helpers (no heavy pipeline imports)."""

from __future__ import annotations

import socket


def lan_ip() -> str:
    """Best-effort LAN IPv4 for this machine (UDP route trick)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()
