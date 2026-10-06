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
import os
import platform
import shutil
import signal
import subprocess
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_OUTPUT = 200_000
MAX_TIMEOUT = 1800
_IS_WIN = platform.system().lower().startswith("win")


def _shell_argv(cmd: str) -> list:
    """How to invoke a command line on this OS. Windows has no /bin/bash, so run
    through cmd.exe; macOS/Linux use a login bash (falls back to sh)."""
    if _IS_WIN:
        comspec = shutil.which("cmd") or "cmd.exe"
        return [comspec, "/c", cmd]
    bash = shutil.which("bash")
    return [bash, "-lc", cmd] if bash else ["/bin/sh", "-lc", cmd]


def _kill_tree(p) -> None:
    """Kill the command AND its children. subprocess's own timeout kills only the
    direct child (the shell), orphaning grandchildren (e.g. a slow `pip`/`nmap`)
    that then keep running and can block the agent. So kill the whole tree."""
    try:
        if _IS_WIN:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        else:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass


def run_command(cmd: str, timeout: int = 120) -> dict:
    """Run a command as a native subprocess on this host; return result dict.
    Shared by the HTTP listener and the heartbeat command handler. OS-aware, and
    on timeout the whole process tree is killed so nothing is left running."""
    timeout = max(1, min(int(timeout), MAX_TIMEOUT))
    t0 = time.time()
    # new session (POSIX) / new process group (Windows) so the whole tree is
    # killable as a unit on timeout.
    kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if _IS_WIN else {"start_new_session": True}
    try:
        p = subprocess.Popen(_shell_argv(cmd), stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, **kw)
    except Exception as e:
        return {"ok": False, "returncode": 1, "stdout": "",
                "stderr": str(e)[:1000], "elapsed": round(time.time() - t0, 2)}
    try:
        out, err = p.communicate(timeout=timeout)
        return {"ok": p.returncode == 0, "returncode": p.returncode,
                "stdout": (out or "")[:MAX_OUTPUT], "stderr": (err or "")[:MAX_OUTPUT],
                "elapsed": round(time.time() - t0, 2)}
    except subprocess.TimeoutExpired:
        _kill_tree(p)
        try:
            out, err = p.communicate(timeout=5)
        except Exception:
            out, err = "", ""
        return {"ok": False, "returncode": 124, "stdout": (out or "")[:MAX_OUTPUT],
                "stderr": (("timed out after %ds\n" % timeout) + (err or ""))[:MAX_OUTPUT],
                "elapsed": timeout}
    except Exception as e:
        _kill_tree(p)
        return {"ok": False, "returncode": 1, "stdout": "",
                "stderr": str(e)[:1000], "elapsed": round(time.time() - t0, 2)}


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
            self._send(200, run_command(cmd, body.get("timeout") or 120))

        def log_message(self, *a):  # silence default stderr logging
            pass

    return Handler


def start_executor(token: str, host: str = "0.0.0.0", port: int = 8899):
    """Start the executor HTTP server in a daemon thread; return the server."""
    srv = ThreadingHTTPServer((host, port), _make_handler(token))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
