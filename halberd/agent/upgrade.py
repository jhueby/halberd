"""Agent self-upgrade (or downgrade) to an operator-pinned version.

Driven by the server's poll: when an agent's running version != its pinned
target, the server returns an {"type":"upgrade", wheel:{url}} directive and the
agent installs that exact wheel and restarts. Like the uninstall teardown, the
pip+restart runs in a transient systemd unit (under PID1, outside this service's
cgroup) so restarting the unit can't kill the installer mid-flight.
"""
from __future__ import annotations

import shlex
import shutil
import subprocess

VENV_PIP = "/opt/halberd-agent/venv/bin/pip"
SERVICE = "halberd-agent.service"


def self_upgrade(wheel_url: str) -> None:
    if not wheel_url:
        return
    # --force-reinstall so it works for both upgrades and downgrades (pip won't
    # move to a lower version otherwise); restart only if the install succeeds.
    script = (
        "%s install --force-reinstall --no-input %s httpx >/dev/null 2>&1 "
        "&& systemctl restart %s"
    ) % (shlex.quote(VENV_PIP), shlex.quote(wheel_url), SERVICE)
    if shutil.which("systemd-run") and shutil.which("systemctl"):
        try:
            # fixed --unit name => a second poll before the restart can't spawn a
            # duplicate (systemd-run refuses a name that is already running).
            subprocess.run(
                ["systemd-run", "--no-block", "--unit=halberd-agent-upgrade",
                 "/bin/bash", "-c", script],
                check=False, timeout=15,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return
        except Exception:
            pass
    try:
        subprocess.Popen(["/bin/sh", "-c", script], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
