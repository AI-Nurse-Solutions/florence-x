"""WorkflowDefinition + WorkflowRun: stateful task graphs, not prompt chains."""
from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import FlorenceModel, utcnow
from .enums import ActionType, DataClass, RiskTier, WorkflowRunStatus


class ActionSpec(FlorenceModel):
    """Describes the CandidateAction a step would emit (optional, overrides inference)."""

    action_type: ActionType
    intended_target: str
    tool_requested: str | None = None
    data_classification: DataClass | None = None  # default: inherit from the Signal
    reversible: bool = True
    external_boundary_crossed: bool = False
    clinical_impact: str | None = None


class WorkflowStep(FlorenceModel):
    step_id: str
    name: str
    agent_id: str | None = None
    produces_action: bool = Field(
        default=False,
        description="If True, this step emits a CandidateAction that must pass EDENA.",
    )
    action: ActionSpec | None = None
    next_steps: list[str] = Field(default_factory=list)


class WorkflowDefinition(FlorenceModel):
    workflow_id: str
    name: str
    version: str = "1.0.0"
    description: str
    signal_types: list[str] = Field(..., description="Signal types this workflow handles.")
    baseline_tier: RiskTier = RiskTier.YELLOW
    steps: list[WorkflowStep]
    owner_role: str
    institutional_approval_ref: str | None = None


class WorkflowRun(FlorenceModel):
    workflow_run_id: str
    workflow_id: str
    signal_id: str
    status: WorkflowRunStatus = WorkflowRunStatus.PENDING
    current_step: str | None = None
    context_id: str | None = None
    started_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None
    evidence_bundle_id: str | None = None
