"""Review-queue API models (Phase 2).

A ReviewItem is the anti-rubber-stamp context a steward needs to decide
meaningfully (docs/safety-model.md): blast radius, reversibility, source
evidence, and EDENA's rationale — never a bare approve button.
"""
from __future__ import annotations

from florence_core.schemas.enums import HumanReviewOutcome
from pydantic import BaseModel


class ReviewItem(BaseModel):
    model_config = {"extra": "forbid"}

    workflow_run_id: str
    workflow_id: str
    status: str

    # The action awaiting judgement.
    action_id: str | None = None
    action_type: str | None = None
    intended_target: str | None = None
    data_classification: str | None = None
    reversible: bool | None = None
    external_boundary_crossed: bool | None = None
    blast_radius_estimate: str | None = None

    # EDENA's verdict and why.
    decision_id: str | None = None
    decision: str | None = None
    risk_tier: str | None = None
    required_human_role: str | None = None
    rationale: str | None = None
    constraints: list[str] = []

    # Source evidence.
    evidence_bundle_id: str | None = None
    source_citations: list[str] = []


class ReviewDecisionRequest(BaseModel):
    """A named human's accountable decision on a paused run."""

    model_config = {"extra": "forbid"}

    outcome: HumanReviewOutcome
    reviewer_ref: str
    reviewer_role: str | None = None
    note: str | None = None
    edited_payload_hash: str | None = None
