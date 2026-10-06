from __future__ import annotations

import os
import platform
import socket
import subprocess
import uuid


def _all_ips() -> str:
    """Best-effort list of this host's non-loopback IPv4 addresses, so the server
    can show where the agent actually lives (the poll's source IP is just the
    Cloudflare tunnel for remote zones). Primary route IP first."""
    ips: list[str] = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.append(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    try:  # every interface (Linux); harmless failure elsewhere
        out = subprocess.run(["ip", "-4", "-o", "addr", "show", "scope", "global"],
                             capture_output=True, text=True, timeout=5).stdout
        for line in out.splitlines():
            for tok in line.split():
                if tok.count(".") == 3 and "/" in tok:
                    ips.append(tok.split("/")[0])
    except Exception:
        pass
    seen: list[str] = []
    for ip in ips:
        if ip and not ip.startswith("127.") and ip not in seen:
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
