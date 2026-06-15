"""Reference EDENA service endpoint.

EDENA is logically a SEPARATE governance service. For the MVP we co-locate a
reference implementation behind its own router so the system runs end-to-end
from a single docker-compose. In production this is split into its own
deployment with its own policy lifecycle. The contract is edena-openapi.yaml.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter

from florence_core.schemas import CandidateAction, EDENADecision
from florence_edena.policy_adapters.local_rules import LocalRuleBackend
from florence_edena.risk_features import extract_risk_features

router = APIRouter(tags=["edena"])
_backend = LocalRuleBackend()


@router.post("/edena/evaluate-action", response_model=EDENADecision)
def evaluate_action(action: CandidateAction) -> EDENADecision:
    raw = _backend.evaluate(extract_risk_features(action))
    return EDENADecision(
        decision_id=f"dec_{uuid.uuid4().hex[:12]}",
        action_id=action.action_id,
        decision=raw["decision"],
        risk_tier=raw["risk_tier"],
        required_human_role=raw.get("required_human_role"),
        constraints=raw.get("constraints", []),
        rationale=raw.get("rationale", ""),
        evidence_required=raw.get("evidence_required", []),
        policy_pack_version="edena-policies-0.1.0",
    )
