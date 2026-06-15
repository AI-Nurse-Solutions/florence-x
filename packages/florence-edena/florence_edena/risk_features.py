"""Deterministic risk-feature extraction from a CandidateAction.

These features are the JSON `input` document handed to the policy engine
(OPA/Rego). Keeping extraction here (not in Rego) means the same features are
auditable, unit-testable, and reusable by Cedar or a future ML risk model.
"""
from __future__ import annotations

from florence_core.schemas import CandidateAction

# Action types that are inherently high-consequence regardless of context.
_HIGH_CONSEQUENCE = {"write_record", "send_message", "execute_code"}
_EXTERNAL_ACTIONS = {"call_api", "send_message", "handoff_to_agent"}


def extract_risk_features(action: CandidateAction) -> dict:
    """Project a CandidateAction into the policy-input document."""
    at = action.action_type if isinstance(action.action_type, str) else action.action_type.value
    dc = (
        action.data_classification
        if isinstance(action.data_classification, str)
        else action.data_classification.value
    )
    return {
        "action_id": action.action_id,
        "action_type": at,
        "data_classification": dc,
        "phi_present": dc in {"phi_local", "phi_redacted"},
        "reversible": action.reversible,
        "external_boundary_crossed": action.external_boundary_crossed,
        "high_consequence_action": at in _HIGH_CONSEQUENCE,
        "external_action": at in _EXTERNAL_ACTIONS,
        "has_clinical_impact": action.clinical_impact is not None,
        "has_financial_impact": action.financial_impact is not None,
        "has_legal_impact": action.legal_or_compliance_impact is not None,
        "requester_role": action.requester_role,
        "tool_requested": action.tool_requested,
        "risk_hint": action.risk_hint if isinstance(action.risk_hint, str) else action.risk_hint.value,
        "evidence_ref_count": len(action.evidence_refs),
    }
