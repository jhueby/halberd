"""Agent self-upgrade (or downgrade) to an operator-pinned version.

Driven by the server's poll: when an agent's running version != its pinned
target, the server returns an {"type":"upgrade", wheel:{url}} directive and the
agent installs that exact wheel and restarts. Per-OS, matching the install:
  * Linux  — venv pip + `systemctl restart`, run in a transient systemd unit
             (under PID1) so restarting the unit can't kill the installer.
  * macOS  — venv pip + `launchctl kickstart -k` of the daemon.
  * Windows— pip into the agent's Python + restart the scheduled task. (A frozen
             halberd.exe install can't pip-upgrade itself; that path needs an
             exe swap and is handled by the installer's upgrade-check, not here.)
"""
from __future__ import annotations

import os
import platform
import shlex
import shutil
import subprocess
import sys

VENV_PIP = "/opt/halberd-agent/venv/bin/pip"
SERVICE = "halberd-agent.service"
MAC_LABEL = "com.halberd.agent"
WIN_TASK = "HalberdAgent"


def _linux_upgrade(wheel_url: str) -> bool:
    script = (
        "%s install --force-reinstall --no-input %s httpx >/dev/null 2>&1 "
        "&& systemctl restart %s"
    ) % (shlex.quote(VENV_PIP), shlex.quote(wheel_url), SERVICE)
    if shutil.which("systemd-run") and shutil.which("systemctl"):
        try:
            subprocess.run(
                ["systemd-run", "--no-block", "--unit=halberd-agent-upgrade",
                 "/bin/bash", "-c", script],
                check=False, timeout=15,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False
    try:
        subprocess.Popen(["/bin/sh", "-c", script], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def _mac_upgrade(wheel_url: str) -> bool:
    script = (
        "%s install --force-reinstall --no-input %s httpx >/dev/null 2>&1 "
        "&& (launchctl kickstart -k system/%s 2>/dev/null || true)"
    ) % (shlex.quote(VENV_PIP), shlex.quote(wheel_url), MAC_LABEL)
    try:
        subprocess.Popen(["/bin/sh", "-c", script], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def _win_upgrade(wheel_url: str) -> bool:
    # Frozen exe can't pip-upgrade itself; only a Python/wheel install can.
    if getattr(sys, "frozen", False):
        return False
    py = sys.executable or "python"
    # Restart the task from a detached cmd so the pip-ing process isn't killed by
    # the task stop. schtasks end/run cycles the agent onto the new version.
    script = (
        '"{py}" -m pip install --force-reinstall --no-input {url} httpx >nul 2>&1 '
        '& schtasks /end /tn {task} >nul 2>&1 '
        '& schtasks /run /tn {task} >nul 2>&1'
    ).format(py=py, url=wheel_url, task=WIN_TASK)
    try:
        subprocess.Popen(["cmd", "/c", script],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
                         | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        return True
    except Exception:
        return False


def self_upgrade(wheel_url: str) -> None:
    if not wheel_url:
        return
    sysname = platform.system().lower()
    if sysname.startswith("win"):
        _win_upgrade(wheel_url)
    elif sysname == "darwin":
        _mac_upgrade(wheel_url)
    else:
        _linux_upgrade(wheel_url)
