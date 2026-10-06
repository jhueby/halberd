from __future__ import annotations

import os
import platform
import re
import socket
import subprocess
import uuid

_QUAD = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3})")


def _iface_ips() -> list[str]:
    """Every interface's IPv4 address, parsed per-OS so we don't mistake a
    gateway (Windows) or broadcast (macOS) for one of our own addresses."""
    sysname = platform.system().lower()
    out = []
    try:
        if sysname.startswith("win"):
            txt = subprocess.run(["ipconfig"], capture_output=True, text=True,
                                 timeout=8).stdout
            for line in txt.splitlines():
                # only the "IPv4 Address. . . : x.x.x.x" lines, not gateway/mask
                if "ipv4" in line.lower():
                    m = _QUAD.search(line)
                    if m:
                        out.append(m.group(1))
        elif sysname == "darwin":
            txt = subprocess.run(["ifconfig"], capture_output=True, text=True,
                                 timeout=8).stdout
            for line in txt.splitlines():
                s = line.strip()
                if s.startswith("inet ") and "inet6" not in s:
                    out.append(s.split()[1])  # token right after "inet"
        else:
            txt = subprocess.run(["ip", "-4", "-o", "addr", "show", "scope", "global"],
                                 capture_output=True, text=True, timeout=8).stdout
            for line in txt.split():
                if line.count(".") == 3 and "/" in line:
                    out.append(line.split("/")[0])
            if not out:  # minimal host without iproute2
                txt = subprocess.run(["ifconfig"], capture_output=True, text=True,
                                     timeout=8).stdout
                for line in txt.splitlines():
                    s = line.strip()
                    if s.startswith("inet ") and "inet6" not in s:
                        tok = s.split()[1]
                        out.append(tok.split(":")[-1] if ":" in tok else tok)
    except Exception:
        pass
    return out


def _all_ips() -> str:
    """Best-effort list of this host's non-loopback IPv4 addresses, so the server
    can show where the agent actually lives (the poll's source IP is just the
    Cloudflare tunnel for remote zones). Primary route IP first. Cross-OS: the
    socket trick is portable; per-interface enumeration is per-OS."""
    ips: list[str] = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.append(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    ips.extend(_iface_ips())
    seen: list[str] = []
    for ip in ips:
        if (ip and not ip.startswith("127.") and not ip.startswith("169.254.")
                and ip != "0.0.0.0" and ip not in seen):
            seen.append(ip)
    return ", ".join(seen)


def _agent_version() -> str:
    try:
        from importlib.metadata import version
        return version("halberd-bas")
    except Exception:
        return "unknown"


def get_platform_info() -> dict[str, str]:
    return {
        "hostname": socket.gethostname(),
        "os": platform.system().lower(),
        "os_version": platform.version(),
        "arch": platform.machine(),
        "kernel": platform.release(),
        "user": os.getenv("USER", os.getenv("USERNAME", "unknown")),
        "is_root": str(os.geteuid() == 0) if hasattr(os, "geteuid") else "false",
        "python_version": platform.python_version(),
        "version": _agent_version(),
        "ip": _all_ips(),
        "agent_id": _get_or_create_agent_id(),
    }


def _get_or_create_agent_id() -> str:
    id_file = os.path.expanduser("~/.halberd-agent-id")
    if os.path.exists(id_file):
        with open(id_file) as f:
            return f.read().strip()
    agent_id = uuid.uuid4().hex[:12]
    try:
        with open(id_file, "w") as f:
            f.write(agent_id)
    except OSError:
        pass
    return agent_id


def current_platform() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    return system
