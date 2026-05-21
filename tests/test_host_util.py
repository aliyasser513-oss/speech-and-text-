"""Tests for LAN IP helper (no pipeline / Whisper)."""

from __future__ import annotations

import socket
from unittest.mock import MagicMock, patch

from host_util import _is_lan_ipv4, _lan_ip_windows_ipconfig, lan_ip


def test_is_lan_ipv4():
    assert _is_lan_ipv4("192.168.1.10")
    assert _is_lan_ipv4("10.0.0.5")
    assert not _is_lan_ipv4("127.0.0.1")
    assert not _is_lan_ipv4("169.254.1.1")


def test_lan_ip_returns_string():
    ip = lan_ip()
    assert isinstance(ip, str)
    parts = ip.split(".")
    assert len(parts) == 4
    assert all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


def test_lan_ip_fallback_when_all_probes_fail():
    with (
        patch("host_util._lan_ip_udp", return_value=None),
        patch("host_util._lan_ip_windows_ipconfig", return_value=None),
        patch("host_util._lan_ip_gethostbyname", return_value=None),
    ):
        assert lan_ip() == "127.0.0.1"


def test_lan_ip_fallback_on_oserror():
    mock_sock = MagicMock()
    mock_sock.connect.side_effect = OSError("no route")
    with (
        patch("host_util.socket.socket", return_value=mock_sock),
        patch("host_util._lan_ip_windows_ipconfig", return_value=None),
        patch("host_util._lan_ip_gethostbyname", return_value=None),
    ):
        assert lan_ip() == "127.0.0.1"


def test_lan_ip_windows_ipconfig_parses_ipv4():
    fake_out = """
Wireless LAN adapter Wi-Fi:
   IPv4 Address. . . . . . . . . . . : 192.168.0.55
"""
    with patch("host_util.subprocess.check_output", return_value=fake_out):
        assert _lan_ip_windows_ipconfig() == "192.168.0.55"


def test_lan_ip_prefers_udp_over_ipconfig():
    with (
        patch("host_util._lan_ip_udp", return_value="10.1.2.3"),
        patch("host_util._lan_ip_windows_ipconfig", return_value="192.168.0.55"),
    ):
        assert lan_ip() == "10.1.2.3"
