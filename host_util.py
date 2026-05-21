"""Small network helpers (no heavy pipeline imports)."""

from __future__ import annotations

import re
import socket
import subprocess
import sys


def _is_lan_ipv4(ip: str) -> bool:
    if not ip or ip.startswith("127.") or ip.startswith("169.254."):
        return False
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        octets = [int(p) for p in parts]
    except ValueError:
        return False
    if octets[0] == 10:
        return True
    if octets[0] == 172 and 16 <= octets[1] <= 31:
        return True
    if octets[0] == 192 and octets[1] == 168:
        return True
    # Other routable private / public LAN (e.g. 192.168.x, some ISP LANs)
    return octets[0] not in (0, 127, 255)


def _lan_ip_udp() -> str | None:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        return ip if _is_lan_ipv4(ip) else None
    except OSError:
        return None
    finally:
        s.close()


def _lan_ip_windows_ipconfig() -> str | None:
    try:
        out = subprocess.check_output(
            ["ipconfig"],
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    # Prefer Wi-Fi / Ethernet sections, then any IPv4 Address
    candidates: list[str] = []
    for line in out.splitlines():
        m = re.search(r"IPv4[^:]*:\s*(\d+\.\d+\.\d+\.\d+)", line, re.I)
        if m:
            candidates.append(m.group(1))

    for ip in candidates:
        if _is_lan_ipv4(ip):
            return ip
    return None


def _lan_ip_gethostbyname() -> str | None:
    try:
        ip = socket.gethostbyname(socket.gethostname())
        return ip if _is_lan_ipv4(ip) else None
    except OSError:
        return None


def lan_ip() -> str:
    """Best-effort LAN IPv4 for this machine."""
    for fn in (_lan_ip_udp, _lan_ip_windows_ipconfig, _lan_ip_gethostbyname):
        if sys.platform != "win32" and fn is _lan_ip_windows_ipconfig:
            continue
        ip = fn()
        if ip:
            return ip
    return "127.0.0.1"
