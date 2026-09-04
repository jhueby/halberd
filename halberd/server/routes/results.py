from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from halberd.library.loader import load_all_atomics
from halberd.server.models import TestRunResult, Campaign
from halberd.server.schemas import ResultsBatch, CoverageEntry

router = APIRouter(prefix="/api/results", tags=["results"])


def get_db():
    from halberd.server.app import get_db_session
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
def submit_results(payload: ResultsBatch, db: Session = Depends(get_db)):
    campaign_id = None
    try:
        campaign_id = int(payload.campaign_id)
    except (ValueError, TypeError):
        pass

    for r in payload.results:
        result = TestRunResult(
            agent_id=payload.agent_id,
            campaign_id=campaign_id,
            technique_id=r.technique_id,
            test_name=r.test_name,
            status=r.status,
            output=r.output,
            error=r.error,
            duration=r.duration,
        )
        db.add(result)

    if campaign_id:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign:
            campaign.status = "completed"
            campaign.completed_at = datetime.now(timezone.utc)

    db.commit()
    return {"status": "recorded", "count": len(payload.results)}


@router.get("/")
def list_results(
    limit: int = 50,
    technique_id: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(TestRunResult).order_by(TestRunResult.timestamp.desc())
    if technique_id:
        query = query.filter(TestRunResult.technique_id == technique_id)
    rows = query.limit(limit).all()
    return [
        {
            "id": r.id,
            "agent_id": r.agent_id,
            "campaign_id": r.campaign_id,
            "technique_id": r.technique_id,
            "test_name": r.test_name,
            "status": r.status,
            "duration": r.duration,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        }
        for r in rows
    ]


@router.get("/coverage", response_model=list[CoverageEntry])
def get_coverage(db: Session = Depends(get_db)):
    techniques = load_all_atomics()

    latest = (
        db.query(
            TestRunResult.technique_id,
            func.max(TestRunResult.timestamp).label("last_tested"),
            TestRunResult.status,
        )
        .group_by(TestRunResult.technique_id)
        .all()
    )
    tested_map = {r.technique_id: (r.status, r.last_tested) for r in latest}

    coverage = []
    for t in techniques:
        tested_info = tested_map.get(t.id)
        coverage.append(CoverageEntry(
            technique_id=t.id,
            technique_name=t.name,
            tactic=t.tactic,
            tested=tested_info is not None,
            last_status=tested_info[0] if tested_info else None,
            last_tested=tested_info[1] if tested_info else None,
        ))

    return coverage
