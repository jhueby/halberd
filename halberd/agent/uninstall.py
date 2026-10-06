"""Agent self-uninstall, triggered when the server tells it (on a poll) that the
operator decommissioned it from the dashboard.

Teardown is per-OS because the install is per-OS:
  * Linux  — systemd unit `halberd-agent.service`; a service can't remove itself
             from inside its own cgroup, so the teardown is handed to a transient
             systemd unit (`systemd-run`) that lives under PID1, then we exit.
  * macOS  — launchd daemon `com.halberd.agent`; bootout + remove the plist and
             the install dir from a detached shell.
  * Windows— scheduled task `HalberdAgent`; delete the task and remove the dir
             from a detached `cmd` that outlives this process.
A foreground / manual run (no service manager) falls through to a best-effort
removal of the install dir and agent-id file.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess

DIR = "/opt/halberd-agent"
SERVICE = "halberd-agent.service"
MAC_LABEL = "com.halberd.agent"
MAC_PLIST = "/Library/LaunchDaemons/com.halberd.agent.plist"
WIN_DIR = os.environ.get("HALBERD_DIR") or r"C:\halberd-agent"
WIN_TASK = "HalberdAgent"

# Linux: disable FIRST so systemd can't auto-restart us (Restart=always) before
# cleanup; then remove the unit, cron entry and install dir.
_TEARDOWN_LINUX = (
    "systemctl disable --now {svc} 2>/dev/null; "
    "rm -f /etc/systemd/system/{svc}; "
    "systemctl daemon-reload 2>/dev/null; "
    "(crontab -l 2>/dev/null | grep -v halberd-upgrade-check | crontab - 2>/dev/null) || true; "
    "rm -rf {dir}; "
    "rm -f /root/.halberd-agent-id \"$HOME/.halberd-agent-id\""
).format(svc=SERVICE, dir=DIR)

_TEARDOWN_MAC = (
    "launchctl bootout system/{label} 2>/dev/null || launchctl unload {plist} 2>/dev/null; "
    "rm -f {plist}; "
    "rm -rf {dir}; "
    "rm -f \"$HOME/.halberd-agent-id\""
).format(label=MAC_LABEL, plist=MAC_PLIST, dir=DIR)


def _linux_uninstall() -> bool:
    if shutil.which("systemd-run") and shutil.which("systemctl"):
        try:
            subprocess.run(
                ["systemd-run", "--no-block", "--unit=halberd-agent-uninstall",
                 "/bin/bash", "-c", _TEARDOWN_LINUX],
                check=True, timeout=15,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False
    return False


def _mac_uninstall() -> bool:
    # launchd will not restart a detached child, so a plain detached shell is fine.
    try:
        subprocess.Popen(["/bin/sh", "-c", "sleep 2; " + _TEARDOWN_MAC],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return True
    except Exception:
        return False


def _win_uninstall() -> bool:
    # Detached cmd outlives us: stop + delete the task, then remove the dir.
    script = (
        'schtasks /end /tn {task} >nul 2>&1 & '
        'schtasks /delete /tn {task} /f >nul 2>&1 & '
        'timeout /t 2 /nobreak >nul & '
        'rmdir /s /q "{dir}" >nul 2>&1 & '
        'del /q "%USERPROFILE%\\.halberd-agent-id" >nul 2>&1'
    ).format(task=WIN_TASK, dir=WIN_DIR)
    try:
        subprocess.Popen(["cmd", "/c", script],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
                         | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        return True
    except Exception:
        return False


def self_uninstall() -> None:
    """Schedule an OS-appropriate teardown that outlives this process, then return
    so the caller can exit."""
    sysname = platform.system().lower()
    ok = False
    if sysname.startswith("win"):
        ok = _win_uninstall()
    elif sysname == "darwin":
        ok = _mac_uninstall()
    else:
        ok = _linux_uninstall()
    if ok:
        return
    # Fallback (no service manager / foreground run): best-effort direct removal.
    try:
        subprocess.Popen(["/bin/sh", "-c", "sleep 2; " + (
            _TEARDOWN_MAC if sysname == "darwin" else _TEARDOWN_LINUX)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
    except Exception:
        try:
            shutil.rmtree(WIN_DIR if sysname.startswith("win") else DIR,
                          ignore_errors=True)
        except Exception:
            pass
