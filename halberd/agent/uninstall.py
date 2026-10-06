"""Agent self-uninstall, triggered when the server tells it (on a poll) that the
operator decommissioned it from the dashboard.

The native Linux install runs the agent as the systemd unit `halberd-agent.service`
(see the installer in Daedalus `agent-installers/install-linux.sh`). A service
can't cleanly remove itself from inside its own cgroup — stopping the unit would
kill the very process doing the cleanup. So we hand the teardown to a transient
systemd unit (`systemd-run`), which lives outside the agent's cgroup, then exit.
"""
from __future__ import annotations

import os
import shutil
import subprocess

DIR = "/opt/halberd-agent"
SERVICE = "halberd-agent.service"

# Disable FIRST so systemd can't auto-restart us (Restart=always) before cleanup;
# then remove the unit, cron entry and install dir. No leading sleep — the
# transient unit runs under PID1 (its own scope), so it outlives this process.
_TEARDOWN = (
    "systemctl disable --now {svc} 2>/dev/null; "
    "rm -f /etc/systemd/system/{svc}; "
    "systemctl daemon-reload 2>/dev/null; "
    "(crontab -l 2>/dev/null | grep -v halberd-upgrade-check | crontab - 2>/dev/null) || true; "
    "rm -rf {dir}; "
    "rm -f /root/.halberd-agent-id \"$HOME/.halberd-agent-id\""
).format(svc=SERVICE, dir=DIR)


def self_uninstall() -> None:
    """Schedule teardown in a transient systemd unit (which runs under PID1, so it
    survives this service's cgroup being torn down), then return so the caller can
    exit. We WAIT for systemd-run to enqueue the job — a previous fire-and-forget
    Popen was killed with our cgroup before the job registered, so the agent came
    back on systemd's restart timer."""
    if shutil.which("systemd-run") and shutil.which("systemctl"):
        try:
            subprocess.run(
                ["systemd-run", "--no-block",
                 "--unit=halberd-agent-uninstall", "/bin/bash", "-c", _TEARDOWN],
                check=True, timeout=15,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return
        except Exception:
            pass
    # No systemd (container/macOS/manual run): best-effort detached shell.
    try:
        subprocess.Popen(
            ["/bin/sh", "-c", "sleep 2; " + _TEARDOWN],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        try:
            shutil.rmtree(DIR, ignore_errors=True)
        except Exception:
            pass
