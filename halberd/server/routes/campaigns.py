from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from halberd.server.models import Campaign
from halberd.server.schemas import CampaignCreate, CampaignInfo, TaskAssignment

router = APIRouter(prefix="/api", tags=["campaigns"])


def get_db():
    from halberd.server.app import get_db_session
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


@router.post("/campaigns", response_model=CampaignInfo)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)):
    campaign = Campaign(
        name=payload.name,
        campaign_type=payload.campaign_type,
        target_ids=payload.target_ids,
        status="pending",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/campaigns", response_model=list[CampaignInfo])
def list_campaigns(db: Session = Depends(get_db)):
    return db.query(Campaign).order_by(Campaign.created_at.desc()).all()


@router.get("/campaigns/{campaign_id}", response_model=CampaignInfo)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("/campaigns/{campaign_id}/start")
def start_campaign(campaign_id: int, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.status = "running"
    db.commit()
    return {"status": "running", "campaign_id": campaign_id}


@router.get("/tasks/{agent_id}")
def get_task(agent_id: str, db: Session = Depends(get_db)):
    campaign = (
        db.query(Campaign)
        .filter(Campaign.status == "running")
        .order_by(Campaign.created_at)
        .first()
    )
    if not campaign or not campaign.target_ids:
        return Response(status_code=204)

    target_id = campaign.target_ids[0]

    if campaign.campaign_type == "chain":
        return TaskAssignment(
            campaign_id=str(campaign.id),
            type="chain",
            chain_id=target_id,
        )
    return TaskAssignment(
        campaign_id=str(campaign.id),
        type="technique",
        technique_id=target_id,
    )
