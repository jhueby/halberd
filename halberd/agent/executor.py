"""Bundled native executor — the agent IS the sandbox executor.

The whole point of an agent is to receive commands from the Daedalus tenant, run
those tools on its OWN network vantage (e.g. a VLAN-40 segment the central box
can't reach), and report results back. This is a small stdlib HTTP server the
agent starts alongside its poll loop; it runs each command as a native
subprocess on the agent host (no Docker) and returns stdout/rc. Bearer-auth with
the agent's API key, so only the tenant (which holds that key) can drive it.
"""
from __future__ import annotations

import hmac
import json
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_OUTPUT = 200_000
MAX_TIMEOUT = 1800


def _make_handler(token: str):
    class Handler(BaseHTTPRequestHandler):
        def _authed(self) -> bool:
            got = self.headers.get("Authorization", "")
            if got.startswith("Bearer "):
                got = got[7:]
            return bool(token) and hmac.compare_digest(got, token)

        def _send(self, code: int, obj: dict) -> None:
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            if self.path.split("?")[0] == "/health":
                return self._send(200, {"ok": True, "executor": "halberd-native",
                                        "ts": int(time.time())})
            self._send(404, {"error": "not found"})

        def do_POST(self):  # noqa: N802
            if not self._authed():
                return self._send(401, {"error": "unauthorized"})
            if self.path.split("?")[0] != "/run":
                return self._send(404, {"error": "not found"})
            try:
                ln = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(ln) or b"{}")
            except Exception:
                return self._send(400, {"error": "bad json"})
            cmd = (body.get("cmd") or "").strip()
            if not cmd:
                return self._send(400, {"error": "cmd required"})
            timeout = max(1, min(int(body.get("timeout") or 120), MAX_TIMEOUT))
            t0 = time.time()
            try:
                p = subprocess.run(["/bin/bash", "-lc", cmd], capture_output=True,
                                   text=True, timeout=timeout)
                self._send(200, {"ok": p.returncode == 0, "returncode": p.returncode,
                                 "stdout": p.stdout[:MAX_OUTPUT], "stderr": p.stderr[:MAX_OUTPUT],
                                 "elapsed": round(time.time() - t0, 2)})
            except subprocess.TimeoutExpired:
                self._send(200, {"ok": False, "returncode": 124, "stdout": "",
                                 "stderr": "timed out after %ds" % timeout, "elapsed": timeout})
            except Exception as e:
                self._send(200, {"ok": False, "returncode": 1, "stdout": "",
                                 "stderr": str(e)[:1000], "elapsed": round(time.time() - t0, 2)})

        def log_message(self, *a):  # silence default stderr logging
            pass

    return Handler


def start_executor(token: str, host: str = "0.0.0.0", port: int = 8899):
    """Start the executor HTTP server in a daemon thread; return the server."""
    srv = ThreadingHTTPServer((host, port), _make_handler(token))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
