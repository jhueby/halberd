from __future__ import annotations

import os
import platform
import socket
import uuid


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
