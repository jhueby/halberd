from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from halberd.server.database import get_engine, get_session_factory, init_db
from halberd.server.routes import agents, library, campaigns, results

_engine = None
_session_factory = None
_TEMPLATES_DIR = Path(__file__).parent / "templates"
_STATIC_DIR = Path(__file__).parent / "static"


def get_db_session() -> Session:
    global _session_factory
    if _session_factory is None:
        _session_factory = get_session_factory(get_engine())
    return _session_factory()


def create_app() -> FastAPI:
    global _engine, _session_factory

    app = FastAPI(
        title="Halberd BAS",
        description="Open-source Breach and Attack Simulation",
        version="0.1.0",
    )

    _engine = get_engine()
    _session_factory = get_session_factory(_engine)
    init_db(_engine)

    app.include_router(agents.router)
    app.include_router(library.router)
    app.include_router(campaigns.router)
    app.include_router(results.router)

    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request):
        from halberd.library.loader import load_all_atomics, load_all_chains

        db = get_db_session()
        try:
            from halberd.server.models import Agent, TestRunResult, Campaign
            from sqlalchemy import func

            agent_count = db.query(Agent).count()
            result_count = db.query(TestRunResult).count()
            campaign_count = db.query(Campaign).count()

            techniques = load_all_atomics()
            chains = load_all_chains()

            from sqlalchemy import and_
            subq = (
                db.query(
                    TestRunResult.technique_id,
                    func.max(TestRunResult.timestamp).label("max_ts"),
                )
                .group_by(TestRunResult.technique_id)
                .subquery()
            )
            latest_results = (
                db.query(TestRunResult)
                .join(
                    subq,
                    and_(
                        TestRunResult.technique_id == subq.c.technique_id,
                        TestRunResult.timestamp == subq.c.max_ts,
                    ),
                )
                .all()
            )
            tested_map = {r.technique_id: r.status for r in latest_results}

            coverage_data = []
            for t in techniques:
                status = tested_map.get(t.id)
                coverage_data.append({
                    "id": t.id,
                    "name": t.name,
                    "tactic": t.tactic,
                    "risk": t.risk.value,
                    "status": status,
                })

            tactics_order = [
                "initial-access", "execution", "persistence", "privilege-escalation",
                "defense-evasion", "credential-access", "discovery", "lateral-movement",
                "collection", "command-and-control", "exfiltration", "impact",
            ]

            return templates.TemplateResponse(request, "dashboard.html", {
                "agent_count": agent_count,
                "result_count": result_count,
                "campaign_count": campaign_count,
                "technique_count": len(techniques),
                "chain_count": len(chains),
                "coverage_data": coverage_data,
                "tactics_order": tactics_order,
            })
        finally:
            db.close()

    @app.get("/library", response_class=HTMLResponse)
    def library_page(request: Request):
        from halberd.library.loader import load_all_atomics, load_all_chains

        techniques = load_all_atomics()
        chains = load_all_chains()
        return templates.TemplateResponse(request, "library.html", {
            "techniques": techniques,
            "chains": chains,
        })

    @app.get("/campaigns", response_class=HTMLResponse)
    def campaigns_page(request: Request):
        db = get_db_session()
        try:
            from halberd.server.models import Campaign
            all_campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
            return templates.TemplateResponse(request, "campaign.html", {
                "campaigns": all_campaigns,
            })
        finally:
            db.close()

    @app.get("/results", response_class=HTMLResponse)
    def results_page(request: Request):
        db = get_db_session()
        try:
            from halberd.server.models import TestRunResult
            all_results = (
                db.query(TestRunResult)
                .order_by(TestRunResult.timestamp.desc())
                .limit(100)
                .all()
            )
            return templates.TemplateResponse(request, "results.html", {
                "results": all_results,
            })
        finally:
            db.close()

    @app.get("/import", response_class=HTMLResponse)
    def import_page(request: Request):
        return templates.TemplateResponse(request, "import.html")

    return app
