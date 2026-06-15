"""AgentDefinition + AgentInvocation: agents are registered labor, not scripts."""
from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import FlorenceModel, utcnow
from .enums import RiskTier


class AgentMemoryRule(FlorenceModel):
    write_allowed: bool = False
    read_allowed: bool = True
    allowed_memory_classes: list[str] = Field(default_factory=list)


class AgentModelRoute(FlorenceModel):
    default: str = Field(..., description="Default model route id, e.g. local_clinical_slm")
    escalation: str | None = None
    phi_rule: str = Field(
        default="never_external_with_phi",
        description="Hard rule for this agent's PHI handling.",
    )


class AgentDefinition(FlorenceModel):
    agent_id: str
    name: str
    version: str = "1.0.0"
    purpose: str
    owner_role: str
    institutional_approval_ref: str | None = None

    allowed_tasks: list[str] = Field(default_factory=list)
    prohibited_tasks: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)

    memory: AgentMemoryRule = Field(default_factory=AgentMemoryRule)
    model_route: AgentModelRoute

    edena_baseline_tier: RiskTier = RiskTier.YELLOW
    evaluation_rubric: str | None = None
    fallback_behavior: str = "return_incomplete_with_missing_flags"
    decommission_path: str = "NAIO-DECOMMISSION-PROCESS"
    active: bool = True


class AgentInvocation(FlorenceModel):
    invocation_id: str
    workflow_run_id: str
    agent_id: str
    step_id: str
    model_route_id: str | None = None
    started_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None
    output_hash: str | None = None
