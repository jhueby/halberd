from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session

from halberd.server.models import Agent
from halberd.server.schemas import AgentRegister, AgentInfo

from halberd.server.auth import require_agent_key

router = APIRouter(prefix="/api/agents", tags=["agents"])


def get_db():
    from halberd.server.app import get_db_session
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


def _source_ip(request: Request) -> str:
    # X-Forwarded-For (behind the Cloudflare tunnel / a reverse proxy) then the socket.
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


@router.post("/register", dependencies=[Depends(require_agent_key)])
def register_agent(payload: AgentRegister, request: Request, db: Session = Depends(get_db)):
    ip = payload.ip or _source_ip(request)       # prefer the agent's self-reported LAN IP(s)
    existing = db.query(Agent).filter(Agent.id == payload.agent_id).first()
    if existing:
        existing.hostname = payload.hostname
        existing.os = payload.os
        existing.os_version = payload.os_version
        existing.arch = payload.arch
        existing.user = payload.user
        existing.is_root = payload.is_root
        existing.python_version = payload.python_version
        existing.version = payload.version
        if ip:
            existing.ip = ip
        # NB: do NOT clear `decommissioned` here — a decommissioned agent that
        # merely restarts must still receive its uninstall directive. A true
        # reinstall mints a new agent_id (its id file is removed), so it lands as
        # a fresh row anyway.
        existing.last_seen = datetime.now(timezone.utc)
    else:
        agent = Agent(
            id=payload.agent_id,
            hostname=payload.hostname,
            os=payload.os,
            os_version=payload.os_version,
            arch=payload.arch,
            user=payload.user,
            is_root=payload.is_root,
            python_version=payload.python_version,
            version=payload.version,
            ip=ip,
        )
        db.add(agent)
    db.commit()
    return {"status": "registered", "agent_id": payload.agent_id}


@router.get("/", response_model=list[AgentInfo])
def list_agents(db: Session = Depends(get_db)):
    return db.query(Agent).all()


@router.get("/{agent_id}", response_model=AgentInfo)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.delete("/{agent_id}", dependencies=[Depends(require_agent_key)])
def decommission_agent(agent_id: str, db: Session = Depends(get_db)):
    """Operator-initiated uninstall: flag the agent so it self-removes on its
    next poll. It stays listed as 'decommissioning' until it confirms via
    /{id}/uninstalled (then it is hard-deleted)."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.decommissioned = 1
    db.commit()
    return {"status": "decommissioning", "agent_id": agent_id}


@router.post("/{agent_id}/uninstalled", dependencies=[Depends(require_agent_key)])
def confirm_uninstalled(agent_id: str, db: Session = Depends(get_db)):
    """Agent confirms it has self-uninstalled; remove it (and its results) for good."""
    from halberd.server.models import TestRunResult
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        return {"status": "gone", "agent_id": agent_id}
    db.query(TestRunResult).filter(TestRunResult.agent_id == agent_id).delete(synchronize_session=False)
    db.delete(agent)
    db.commit()
    return {"status": "removed", "agent_id": agent_id}
