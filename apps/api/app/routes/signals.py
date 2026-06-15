"""Signal intake.

By default `POST /signals` enqueues the signal for async processing and returns
202 with a pollable workflow_run_id (P1-8); a worker drains the queue and runs the
governed workflow. Pass `sync=true` to run inline and get the EvidenceBundle back
(handy for demos and tests).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response, status

from florence_core.schemas import Signal

from ..queue import SignalAccepted
from ..services import get_orchestrator

router = APIRouter(tags=["signals"])


@router.post("/signals", status_code=status.HTTP_202_ACCEPTED)
def submit_signal(signal: Signal, response: Response,
                  sync: bool = Query(False, description="Run inline and return the EvidenceBundle."),
                  auto_approve: bool = Query(False)):
    orch = get_orchestrator()
    try:
        if sync:
            response.status_code = status.HTTP_200_OK
            return orch.submit(signal, auto_approve=auto_approve)
        accepted: SignalAccepted = orch.enqueue(signal, auto_approve=auto_approve)
        return accepted
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
