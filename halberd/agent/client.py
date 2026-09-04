from __future__ import annotations

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
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
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
                time.sleep(self.poll_interval)
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

        results: list[TestResult] = []
        if task_type == "technique":
            results = run_technique(task["technique_id"], self.sandbox)
        elif task_type == "chain":
            chain = load_chain(task["chain_id"])
            results = run_chain(chain, self.sandbox)

        self.report_results(campaign_id, results)
        print(f"Reported {len(results)} results for campaign {campaign_id}")
