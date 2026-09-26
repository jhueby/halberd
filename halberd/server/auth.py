"""Optional API-key auth for agent-facing routes.

Backward-compatible: if HALBERD_API_KEY is unset/empty (the default), enforcement
is disabled and everything works as before — safe for LAN-only deployments. Set
HALBERD_API_KEY on the server to require agents to present the same key as a
Bearer token (agents already send `Authorization: Bearer <key>`), which matters
once the server is exposed beyond the LAN (e.g. via a tunnel).
"""
from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException, status


def require_agent_key(authorization: str = Header(default="")) -> None:
    expected = os.environ.get("HALBERD_API_KEY", "")
    if not expected:
        return  # enforcement disabled
    token = authorization[7:] if authorization.startswith("Bearer ") else ""
    if not token or not hmac.compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing agent API key",
        )
