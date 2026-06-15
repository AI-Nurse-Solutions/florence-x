"""ToolDefinition: tools are dangerous until proven bounded."""
from __future__ import annotations

from pydantic import Field

from .common import FlorenceModel
from .enums import RiskTier, ToolRiskClass


class ToolDefinition(FlorenceModel):
    tool_id: str
    name: str
    description: str
    risk_class: ToolRiskClass
    transport: str = Field(
        default="mcp", description="mcp | fhir | smart | cds_hooks | openapi | a2a | rpa | local"
    )
    allowed_actions: list[str] = Field(
        ..., description="Explicit allow-list. Anything not listed is denied."
    )
    review_tier_trigger: RiskTier = Field(
        default=RiskTier.YELLOW,
        description="EDENA tier at/above which a human must review invocation.",
    )
    audit_rules: list[str] = Field(default_factory=list)
    failure_mode: str = Field(..., description="What happens when the tool fails / returns junk.")
    owner_role: str
