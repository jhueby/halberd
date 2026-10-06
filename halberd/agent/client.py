from __future__ import annotations

import os
import time

from halberd.agent.platform_info import get_platform_info
from halberd.agent.runner import run_technique, run_chain, TestResult
from halberd.agent.sandbox import Sandbox
from halberd.library.loader import load_chain


class AgentClient:
    """Connects to the Halberd server, polls for tasks, reports results."""

    def __init__(
        self,
        server_url: str,
        api_key: str,
        sandbox: Sandbox,
        poll_interval: int = 30,
    ):
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.sandbox = sandbox
        self.poll_interval = poll_interval
        self.info = get_platform_info()
        self.agent_id = self.info["agent_id"]

    def _headers(self) -> dict[str, str]:
        # A non-generic User-Agent is required: fronting proxies (e.g. Cloudflare
        # Bot Fight Mode) reject the default httpx UA ("python-httpx/*").
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": f"halberd-agent/{self.info.get('version', 'dev')}",
        }

    def register(self) -> None:
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx is required for agent mode: pip install 'halberd-bas[agent]'")

        resp = httpx.post(
            f"{self.server_url}/api/agents/register",
            json=self.info,
            headers=self._headers(),
            timeout=10,
        )
        resp.raise_for_status()
        print(f"Registered agent {self.agent_id} with server")

    def heartbeat(self) -> dict | None:
        import httpx

        resp = httpx.get(
            f"{self.server_url}/api/tasks/{self.agent_id}",
            headers=self._headers(),
            timeout=10,
        )
        if resp.status_code == 204:
            return None
        resp.raise_for_status()
        return resp.json()

    def report_results(self, campaign_id: str, results: list[TestResult]) -> None:
        import httpx

        payload = {
            "agent_id": self.agent_id,
            "campaign_id": campaign_id,
            "results": [
                {
                    "technique_id": r.technique_id,
                    "test_name": r.test_name,
                    "status": r.status,
                    "output": r.output,
                    "error": r.error,
                    "duration": r.duration,
                    "timestamp": r.timestamp,
                }
                for r in results
            ],
        }
        resp = httpx.post(
            f"{self.server_url}/api/results/",
            json=payload,
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()

    def run_loop(self) -> None:
        self.register()
        print(f"Polling {self.server_url} every {self.poll_interval}s...")

        while True:
            try:
                task = self.heartbeat()
                if task:
                    self._execute_task(task)
                # after handling something, re-poll quickly to drain a command burst;
                # otherwise wait the normal heartbeat interval.
                time.sleep(2 if task else self.poll_interval)
            except KeyboardInterrupt:
                print("Agent stopped")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(self.poll_interval)

    def _execute_task(self, task: dict) -> None:
        campaign_id = task.get("campaign_id", "unknown")
        task_type = task.get("type", "technique")

        print(f"Received task: {task_type} (campaign {campaign_id})")

        if task_type == "decommission":
            self._decommission()
            return

        if task_type == "upgrade":
            url = (task.get("wheel") or {}).get("url") or task.get("wheel_url")
            print(f"Upgrade directive -> {task.get('version')} ({url})")
            try:
                from halberd.agent.upgrade import self_upgrade
                self_upgrade(url)
            except Exception as e:
                print(f"(upgrade launch failed: {e})")
            return

        if task_type == "command":
            self._run_command(task)
            return

        results: list[TestResult] = []
        if task_type == "technique":
            results = run_technique(task["technique_id"], self.sandbox)
        elif task_type == "chain":
            chain = load_chain(task["chain_id"])
            results = run_chain(chain, self.sandbox)

        self.report_results(campaign_id, results)
        print(f"Reported {len(results)} results for campaign {campaign_id}")

    def _run_command(self, task: dict) -> None:
        """Run a tenant-queued command on this host and post the result back."""
        import httpx
        cid = task.get("command_id")
        cmd = task.get("cmd") or ""
        to = int(task.get("timeout") or 120)
        print(f"Command #{cid}: {cmd[:80]}")
        from halberd.agent.executor import run_command
        res = run_command(cmd, to)
        try:
            httpx.post(
                f"{self.server_url}/api/agents/{self.agent_id}/command-result",
                headers=self._headers(),
                json={"command_id": cid, "returncode": res.get("returncode"),
                      "stdout": res.get("stdout"), "stderr": res.get("stderr"),
                      "elapsed": res.get("elapsed")},
                timeout=30,
            )
        except Exception as e:
            print(f"(command-result post failed: {e})")

    def _decommission(self) -> None:
        """Operator removed us from the dashboard: tell the server we're gone,
        schedule our own teardown, and exit."""
        print("Decommission requested by server — uninstalling self")
        try:
            import httpx
            httpx.post(
                f"{self.server_url}/api/agents/{self.agent_id}/uninstalled",
                headers=self._headers(), timeout=10,
            )
        except Exception as e:
            print(f"(confirm-uninstall failed, continuing: {e})")
        try:
            from halberd.agent.uninstall import self_uninstall
            self_uninstall()
        except Exception as e:
            print(f"(teardown launch failed: {e})")
        os._exit(0)
