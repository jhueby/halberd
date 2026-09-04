from __future__ import annotations

from fastapi import APIRouter, HTTPException

from halberd.library.loader import load_all_atomics, load_all_chains, load_atomic, load_chain
from halberd.library.importer import import_chain, FileImporter, URLImporter
from halberd.server.schemas import TechniqueInfo, ChainInfo, ImportRequest

router = APIRouter(prefix="/api/library", tags=["library"])


@router.get("/techniques", response_model=list[TechniqueInfo])
def list_techniques():
    techniques = load_all_atomics()
    return [
        TechniqueInfo(
            id=t.id,
            name=t.name,
            tactic=t.tactic,
            platforms=[p.value for p in t.platforms],
            risk=t.risk.value,
            description=t.description,
            test_count=len(t.tests),
        )
        for t in techniques
    ]


@router.get("/techniques/{technique_id}")
def get_technique(technique_id: str):
    try:
        t = load_atomic(technique_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Technique {technique_id} not found")
    return t.model_dump()


@router.get("/chains", response_model=list[ChainInfo])
def list_chains():
    chains = load_all_chains()
    return [
        ChainInfo(
            id=c.id,
            name=c.name,
            description=c.description,
            mitre_tactics=c.mitre_tactics,
            step_count=len(c.steps),
            import_source=c.import_source,
        )
        for c in chains
    ]


@router.get("/chains/{chain_id}")
def get_chain(chain_id: str):
    try:
        c = load_chain(chain_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Chain {chain_id} not found")
    return c.model_dump()


@router.post("/import")
def import_chain_endpoint(req: ImportRequest):
    backend = None
    if req.source_type == "file":
        backend = FileImporter()
    elif req.source_type == "url":
        backend = URLImporter()

    try:
        chain = import_chain(req.source, backend=backend, save=True)
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "imported",
        "chain_id": chain.id,
        "name": chain.name,
        "steps": len(chain.steps),
    }
