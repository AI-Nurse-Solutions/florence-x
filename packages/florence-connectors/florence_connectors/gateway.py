"""ToolGateway — the single policy-enforcement point for tool execution (RFC 0004).

Agents never call tools directly (OWASP ASI02). Every invocation is a
CandidateAction that EDENA must clear *and* whose tool must be explicitly
registered — tools are deny-by-default (CLAUDE.md rule 8). A2A handoffs flow
through here too: a handoff is just another CandidateAction.

The gateway is transport-agnostic: it multiplexes registered Connectors
(fhir | mcp | smart | cds_hooks | openapi | a2a | local) behind one gate.
"""
from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from florence_core.schemas import CandidateAction
from florence_core.schemas.enums import EdenaDecisionType

from .base import Connector

_ALLOWED = {EdenaDecisionType.ALLOW.value, EdenaDecisionType.ALLOW_WITH_CONSTRAINTS.value}


@dataclass
class ToolBinding:
    connector: Connector
    action: str  # the connector-level action this tool_id maps to


class GatewayResult(BaseModel):
    model_config = {"extra": "forbid"}

    executed: bool
    refused: bool = False
    decision: str | None = None
    risk_tier: str | None = None
    reason: str | None = None
    result: dict | None = None


class ToolGateway:
    def __init__(self, edena) -> None:
        # `edena` is any object with evaluate_action(CandidateAction) -> EDENADecision.
        self.edena = edena
        self._registry: dict[str, ToolBinding] = {}

    def register(self, tool_id: str, connector: Connector, action: str) -> None:
        self._registry[tool_id] = ToolBinding(connector, action)

    def registered_tools(self) -> list[str]:
        return sorted(self._registry)

    def invoke(self, action: CandidateAction, payload: dict | None = None) -> GatewayResult:
        # 1. EDENA gate — no tool runs without a clearing decision.
        decision = self.edena.evaluate_action(action)
        if decision.decision not in _ALLOWED:
            return GatewayResult(executed=False, refused=True, decision=decision.decision,
                                 risk_tier=decision.risk_tier,
                                 reason=f"edena_{decision.decision}")
        # 2. Deny-by-default tool boundary — the tool must be explicitly registered.
        binding = self._registry.get(action.tool_requested or "")
        if binding is None:
            return GatewayResult(executed=False, refused=True, decision=decision.decision,
                                 risk_tier=decision.risk_tier, reason="tool_not_registered")
        # 3. Bounded execution through the connector.
        result = binding.connector.invoke(binding.action, payload or {})
        return GatewayResult(executed=True, decision=decision.decision,
                             risk_tier=decision.risk_tier, result=result)
