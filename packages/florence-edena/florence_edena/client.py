"""EdenaClient — Florence-X's only path to a governance decision.

The client is *fail-closed*: if the governance plane cannot be reached or
errors, it returns a safe non-executing decision (require_human, or deny for
irreversible/external actions). EDENA never fails *open*.

Backends:
  * HttpBackend        -> POST {base_url}/edena/evaluate-action  (separate service)
  * LocalOpaBackend    -> `opa eval` against policies/edena/*.rego (sidecar/CLI)
  * LocalRuleBackend   -> pure-Python mirror of the Rego packs (no deps; MVP/tests)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Protocol

from florence_core.observability import set_attributes, span
from florence_core.schemas import CandidateAction, EDENADecision
from florence_core.schemas.enums import EdenaDecisionType, RiskTier

from .policy_adapters.local_rules import LocalRuleBackend
from .risk_features import extract_risk_features


class EvaluateBackend(Protocol):
    def evaluate(self, features: dict) -> dict:  # returns raw decision dict
        ...


@dataclass
class EdenaConfig:
    base_url: str | None = None
    timeout_s: float = 2.0
    fail_closed: bool = True
    policy_pack_version: str = "edena-policies-0.1.0"


def make_backend(config: EdenaConfig) -> EvaluateBackend:
    """Select the decision backend from config (P1-12).

    A configured ``base_url`` (e.g. EDENA_BASE_URL=http://opa:8181) routes through
    a running OPA server; otherwise the MVP uses the pure-Python LocalRuleBackend.
    Both produce the same decision shape, so parity holds across the toggle.
    """
    if config.base_url:
        from .policy_adapters.opa import OpaHttpBackend

        return OpaHttpBackend(config.base_url, timeout_s=config.timeout_s)
    return LocalRuleBackend()


def _safe_fallback(action: CandidateAction, reason: str) -> EDENADecision:
    """When governance is unavailable, deny irreversible/external work; else require a human."""
    block = (not action.reversible) or action.external_boundary_crossed
    return EDENADecision(
        decision_id=f"dec_{uuid.uuid4().hex[:12]}",
        action_id=action.action_id,
        decision=EdenaDecisionType.DENY if block else EdenaDecisionType.REQUIRE_HUMAN,
        risk_tier=RiskTier.RED if block else RiskTier.YELLOW,
        required_human_role=None if block else action.requester_role,
        rationale=f"FAIL-CLOSED: {reason}",
    )


@dataclass
class EdenaClient:
    config: EdenaConfig = field(default_factory=EdenaConfig)
    backend: EvaluateBackend | None = None

    def __post_init__(self) -> None:
        if self.backend is None:
            self.backend = make_backend(self.config)

    def evaluate_action(self, action: CandidateAction) -> EDENADecision:
        features = extract_risk_features(action)
        with span("florence.edena.evaluate",
                  action_id=action.action_id, action_type=action.action_type,
                  backend=type(self.backend).__name__) as sp:
            try:
                raw = self.backend.evaluate(features)
            except Exception as exc:  # noqa: BLE001 - governance must never crash the loop
                if self.config.fail_closed:
                    fallback = _safe_fallback(action, f"backend error: {exc}")
                    set_attributes(sp, **{"edena.fail_closed": True,
                                          "edena.decision": fallback.decision,
                                          "edena.risk_tier": fallback.risk_tier})
                    return fallback
                raise
            set_attributes(sp, **{"edena.decision": raw["decision"],
                                  "edena.risk_tier": raw["risk_tier"]})
            return EDENADecision(
                decision_id=f"dec_{uuid.uuid4().hex[:12]}",
                action_id=action.action_id,
                decision=raw["decision"],
                risk_tier=raw["risk_tier"],
                required_human_role=raw.get("required_human_role"),
                constraints=raw.get("constraints", []),
                rationale=raw.get("rationale", ""),
                evidence_required=raw.get("evidence_required", []),
                policy_pack_version=self.config.policy_pack_version,
            )
