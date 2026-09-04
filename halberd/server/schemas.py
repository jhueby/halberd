from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AgentRegister(BaseModel):
    agent_id: str
    hostname: str
    os: str
    os_version: str = ""
    arch: str = ""
    user: str = ""
    is_root: str = "false"
    python_version: str = ""


class AgentInfo(BaseModel):
    id: str
    hostname: str
    os: str
    last_seen: datetime | None = None

    model_config = {"from_attributes": True}


class TaskAssignment(BaseModel):
    campaign_id: str
    type: str  # technique or chain
    technique_id: str | None = None
    chain_id: str | None = None


class TestResultSubmit(BaseModel):
    technique_id: str
    test_name: str
    status: str
    output: str = ""
    error: str = ""
    duration: float = 0.0
    timestamp: str = ""


class ResultsBatch(BaseModel):
    agent_id: str
    campaign_id: str
    results: list[TestResultSubmit]


class CampaignCreate(BaseModel):
    name: str
    campaign_type: str = "technique"
    target_ids: list[str] = Field(default_factory=list)


class CampaignInfo(BaseModel):
    id: int
    name: str
    campaign_type: str
    status: str
    target_ids: list[str]
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ImportRequest(BaseModel):
    source: str
    source_type: str = "auto"  # auto, file, url


class TechniqueInfo(BaseModel):
    id: str
    name: str
    tactic: str
    platforms: list[str]
    risk: str
    description: str
    test_count: int


class ChainInfo(BaseModel):
    id: str
    name: str
    description: str
    mitre_tactics: list[str]
    step_count: int
    import_source: str | None = None


class CleanupRequest(BaseModel):
    technique_id: str | None = None
    all: bool = False
    check_only: bool = False


class CoverageEntry(BaseModel):
    technique_id: str
    technique_name: str
    tactic: str
    tested: bool = False
    last_status: str | None = None
    last_tested: datetime | None = None
