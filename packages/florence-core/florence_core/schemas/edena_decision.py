"""EDENADecision — the governance plane's verdict on a CandidateAction.

This type is defined in florence-core (the shared contract layer) so that both
the orchestration plane and the evidence layer can depend on it without creating
a circular dependency on florence-edena. florence-edena re-exports it.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import FlorenceModel, utcnow
from .enums import EdenaDecisionType, RiskTier


class EDENADecision(FlorenceModel):
    decision_id: str
    action_id: str
    decision: EdenaDecisionType
    risk_tier: RiskTier
    required_human_role: str | None = None
    constraints: list[str] = Field(default_factory=list)
    rationale: str
    evidence_required: list[str] = Field(default_factory=list)
    policy_pack_version: str | None = None
    decided_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime | None = None

    @property
    def requires_human(self) -> bool:
        return self.decision in {
            EdenaDecisionType.REQUIRE_HUMAN.value,
            EdenaDecisionType.ESCALATE.value,
            EdenaDecisionType.REQUIRE_HUMAN,
            EdenaDecisionType.ESCALATE,
        }

    @property
    def is_terminal_block(self) -> bool:
        # deny / stop / contain are all non-executing terminal outcomes: the action
        # never runs. (contain additionally implies isolation/containment actions.)
        return self.decision in {
            EdenaDecisionType.DENY.value,
            EdenaDecisionType.STOP.value,
            EdenaDecisionType.CONTAIN.value,
            EdenaDecisionType.DENY,
            EdenaDecisionType.STOP,
            EdenaDecisionType.CONTAIN,
        }

    @property
    def is_containment(self) -> bool:
        return self.decision in {EdenaDecisionType.CONTAIN.value, EdenaDecisionType.CONTAIN}
