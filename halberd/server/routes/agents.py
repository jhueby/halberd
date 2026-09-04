from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from halberd.server.models import Agent
from halberd.server.schemas import AgentRegister, AgentInfo

router = APIRouter(prefix="/api/agents", tags=["agents"])


def get_db():
    from halberd.server.app import get_db_session
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


@router.post("/register")
def register_agent(payload: AgentRegister, db: Session = Depends(get_db)):
    existing = db.query(Agent).filter(Agent.id == payload.agent_id).first()
    if existing:
        existing.hostname = payload.hostname
        existing.os = payload.os
        existing.os_version = payload.os_version
        existing.arch = payload.arch
        existing.user = payload.user
        existing.is_root = payload.is_root
        existing.python_version = payload.python_version
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
