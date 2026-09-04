from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from .database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(32), primary_key=True)
    hostname = Column(String(256))
    os = Column(String(64))
    os_version = Column(String(128))
    arch = Column(String(32))
    user = Column(String(128))
    is_root = Column(String(8))
    python_version = Column(String(32))
    last_seen = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    registered_at = Column(DateTime, default=_utcnow)

    results = relationship("TestRunResult", back_populates="agent")


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False)
    campaign_type = Column(String(32))  # technique, chain, custom
    target_ids = Column(JSON, default=list)  # technique or chain IDs
    status = Column(String(32), default="pending")  # pending, running, completed
    created_at = Column(DateTime, default=_utcnow)
    completed_at = Column(DateTime, nullable=True)

    results = relationship("TestRunResult", back_populates="campaign")


class TestRunResult(Base):
    __tablename__ = "test_run_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(32), ForeignKey("agents.id"), nullable=False)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    technique_id = Column(String(32), nullable=False)
    test_name = Column(String(256))
    status = Column(String(32))  # success, failed, skipped, error, dry-run
    output = Column(Text, default="")
    error = Column(Text, default="")
    duration = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=_utcnow)

    agent = relationship("Agent", back_populates="results")
    campaign = relationship("Campaign", back_populates="results")


class ImportedChain(Base):
    __tablename__ = "imported_chains"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chain_id = Column(String(128), unique=True, nullable=False)
    name = Column(String(256))
    source = Column(Text)
    imported_at = Column(DateTime, default=_utcnow)
    raw_yaml = Column(Text)
