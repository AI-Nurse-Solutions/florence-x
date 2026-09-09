"""Human review queue (Phase 2).

A Yellow+ action pauses its run (LangGraph interrupt, P1-9); the paused run shows
up here with full context, and a steward resolves it — Approve / Edit / Escalate /
Deny / Stop. Approval resumes the run to completion; deny/stop block it and create
an Incident.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from florence_core.schemas import EvidenceBundle, Incident, PolicyPack

from ..review import ReviewDecisionRequest, ReviewItem
from ..services import get_orchestrator

router = APIRouter(tags=["reviews"])


@router.get("/reviews", response_model=list[ReviewItem])
def list_reviews() -> list[ReviewItem]:
    return get_orchestrator().list_reviews()


@router.get("/reviews/{workflow_run_id}", response_model=ReviewItem)
def get_review(workflow_run_id: str) -> ReviewItem:
    try:
        return get_orchestrator().get_review(workflow_run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/reviews/{workflow_run_id}", response_model=EvidenceBundle)
def submit_review(workflow_run_id: str, decision: ReviewDecisionRequest) -> EvidenceBundle:
    orch = get_orchestrator()
    try:
        return orch.submit_review(workflow_run_id, decision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:  # resume requires the graph runtime
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/incidents", response_model=list[Incident], tags=["incidents"])
def list_incidents() -> list[Incident]:
    return get_orchestrator().incidents()


@router.get("/policy-packs", response_model=list[PolicyPack], tags=["policy"])
def list_policy_packs() -> list[PolicyPack]:
    return get_orchestrator().policy_packs()
