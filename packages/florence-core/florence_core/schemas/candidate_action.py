"""CandidateAction — the most important object in Florence-X.

This is the single point where AI output crosses from *generation* into
*governed action*. Nothing consequential executes until a CandidateAction has
been evaluated by EDENA (see florence_edena, docs/edena-integration.md).

Design rules:
  * Carry a *hash* of the proposed payload, never the payload itself, so the
    governance plane reasons over metadata, not raw PHI.
  * `external_boundary_crossed` and `reversible` are first-class because
    Externality raises the floor and Reversibility determines risk (EDENA).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import FlorenceModel, utcnow
from .enums import ActionType, DataClass, RiskTier


class CandidateAction(FlorenceModel):
    action_id: str
    workflow_run_id: str
    agent_id: str
    requester_role: str

    action_type: ActionType
    intended_target: str = Field(..., description="The system/resource the action would touch.")
    tool_requested: str | None = None

    data_classification: DataClass
    reversible: bool
    external_boundary_crossed: bool

    clinical_impact: str | None = None
    financial_impact: str | None = None
    legal_or_compliance_impact: str | None = None

    proposed_payload_hash: str = Field(..., description="Hash of content, NOT the content itself.")
    evidence_refs: list[str] = Field(default_factory=list)

    risk_hint: RiskTier = Field(
        default=RiskTier.YELLOW,
        description="Orchestrator's first guess; EDENA owns the final tier.",
    )
    blast_radius_estimate: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
