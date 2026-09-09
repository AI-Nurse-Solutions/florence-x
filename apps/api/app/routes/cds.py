"""CDS Hooks + SMART on FHIR surface (Phase 4).

CDS Hooks invocations become governed Signals; the response is CDS cards that
summarize EDENA's decision (incl. "pending steward review" when a run pauses) —
never an ungoverned recommendation.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from florence_connectors.cds_hooks import discovery, signal_from_request
from florence_connectors.smart import SmartLaunchContext
from florence_connectors.smart import launch as build_launch_context

from ..services import get_orchestrator

router = APIRouter(tags=["cds-hooks"])

# EDENA tier → CDS Hooks card indicator.
_INDICATOR = {"green": "info", "yellow": "info", "orange": "warning",
              "red": "critical", "red_blocked": "critical"}


@router.get("/cds-services")
def cds_services() -> dict:
    return discovery()


@router.post("/cds-services/{service_id}")
def invoke_cds_service(service_id: str, request: dict) -> dict:
    try:
        signal = signal_from_request(service_id, request, signal_id=f"cds_{uuid.uuid4().hex[:10]}")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        bundle = get_orchestrator().submit(signal)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    decision = bundle.edena_decisions[-1] if bundle.edena_decisions else None
    tier = decision.risk_tier if decision else "green"
    detail = decision.rationale if decision else "No governed action proposed."
    if bundle.final_action == "awaiting_human_review":
        detail += f"\n\nPending steward review — run {bundle.workflow_run_id}."
    return {
        "cards": [
            {
                "summary": f"{signal.signal_type}: EDENA {decision.decision if decision else 'allow'} ({tier})",
                "indicator": _INDICATOR.get(tier, "info"),
                "detail": detail,
                "source": {"label": "Florence-X", "url": "https://florence-x.local"},
            }
        ]
    }


@router.get("/smart/launch", response_model=SmartLaunchContext)
def smart_launch(iss: str, launch: str, patient: str | None = None,
                 encounter: str | None = None) -> SmartLaunchContext:
    try:
        return build_launch_context(iss, launch, patient=patient, encounter=encounter)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
