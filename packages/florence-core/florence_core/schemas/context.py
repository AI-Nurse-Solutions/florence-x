"""Layer 2 — ContextBundle: the approved context handed to an agent."""
from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import FlorenceModel, utcnow
from .enums import DataClass


class ContextBundle(FlorenceModel):
    context_id: str
    workflow_run_id: str
    data_classification: DataClass
    phi_present: bool
    redacted: bool = False
    minimum_necessary_justification: str
    source_refs: list[str] = Field(
        default_factory=list, description="FHIR resource IDs, policy doc versions, etc."
    )
    content_hash: str = Field(..., description="Hash of materialized context, not the content.")
    consent_constraints: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
