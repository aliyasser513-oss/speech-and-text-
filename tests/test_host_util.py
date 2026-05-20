"""Tests for LAN IP helper (no pipeline / Whisper)."""

from __future__ import annotations

import socket
from unittest.mock import MagicMock, patch

from host_util import lan_ip


def test_lan_ip_returns_string():
    ip = lan_ip()
    assert isinstance(ip, str)
    parts = ip.split(".")
    assert len(parts) == 4
    assert all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


def test_lan_ip_fallback_on_oserror():
    mock_sock = MagicMock()
    mock_sock.connect.side_effect = OSError("no route")
    with patch("host_util.socket.socket", return_value=mock_sock):
        assert lan_ip() == "127.0.0.1"
