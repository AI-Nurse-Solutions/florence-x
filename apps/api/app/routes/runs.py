"""Read-only access to run state + evidence bundles."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from florence_core.schemas import EvidenceBundle, WorkflowRun

from ..services import get_orchestrator

router = APIRouter(tags=["runs"])


@router.get("/runs/{workflow_run_id}", response_model=WorkflowRun)
def get_run(workflow_run_id: str) -> WorkflowRun:
    run = get_orchestrator().repo.get_run(workflow_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.get("/runs/{workflow_run_id}/evidence", response_model=EvidenceBundle)
def get_evidence(workflow_run_id: str) -> EvidenceBundle:
    repo = get_orchestrator().repo
    run = repo.get_run(workflow_run_id)
    if run is None or run.evidence_bundle_id is None:
        raise HTTPException(status_code=404, detail="evidence not found")
    bundle = repo.get_evidence(run.evidence_bundle_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="evidence not found")
    return bundle
