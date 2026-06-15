"""Layer 1 — Signal: every input becomes a typed, classified event."""
from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import FlorenceModel, RequesterContext, utcnow
from .enums import DataClass, Urgency


class CDSHookContext(FlorenceModel):
    """HL7 CDS Hooks invocation context (workflow-triggered decision support)."""

    hook: str = Field(..., description="e.g. patient-view, order-select, order-sign")
    hook_instance: str
    fhir_server: str | None = None
    context: dict = Field(default_factory=dict)


class Signal(FlorenceModel):
    signal_id: str
    source: str = Field(..., description='e.g. "ehr.event", "nurse.request", "cds_hooks"')
    signal_type: str = Field(..., description='e.g. "icu_handoff_needed"')
    requester: RequesterContext
    data_classification: DataClass
    urgency: Urgency = Urgency.ROUTINE
    patient_context_present: bool = False
    cds_hook_context: CDSHookContext | None = None
    payload_ref: str | None = Field(
        default=None, description="Pointer to payload in the data boundary; never inline PHI."
    )
    created_at: datetime = Field(default_factory=utcnow)
