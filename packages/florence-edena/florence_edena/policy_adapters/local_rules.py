"""LocalRuleBackend — a pure-Python mirror of the Rego policy packs.

Why this exists: the MVP and the test suite must produce real, deterministic
EDENA decisions WITHOUT requiring an OPA binary on the developer's machine.
This backend encodes the same decision ladder as policies/edena/*.rego and is
kept in sync via tests/policy/test_parity.py.

Decision ladder (highest precedence first) — Ambiguity escalates upward:
  1. RED-BLOCKED  restricted data, or code execution on production -> DENY
  2. RED          EHR write / patient message / medication-adjacent -> REQUIRE_HUMAN (clinician + compliance)
  3. ORANGE       code execution, or external boundary crossed      -> REQUIRE_HUMAN (senior + technical steward)
  4. YELLOW       PHI-bearing clinical draft/summarize              -> REQUIRE_HUMAN (clinician)
  5. GREEN        bounded, reversible, informational                -> ALLOW / ALLOW_WITH_CONSTRAINTS
"""
from __future__ import annotations


def _decide(f: dict) -> dict:
    at = f["action_type"]
    target = (f.get("tool_requested") or "") + " " + str(f.get("action_id", ""))
    target_l = target.lower()

    # 1. RED-BLOCKED ---------------------------------------------------------
    if f["data_classification"] == "restricted":
        return {
            "decision": "deny",
            "risk_tier": "red_blocked",
            "rationale": "Restricted data (secrets/credentials) may not be used in an action.",
        }
    if at == "execute_code" and ("prod" in target_l or "production" in target_l):
        return {
            "decision": "deny",
            "risk_tier": "red_blocked",
            "rationale": "Code execution against production is prohibited without an override chain.",
        }

    # 2. RED -----------------------------------------------------------------
    if at == "write_record":
        return {
            "decision": "require_human",
            "risk_tier": "red",
            "required_human_role": "clinician",
            "constraints": ["must_not_finalize_without_named_clinician", "compliance_cosign_required"],
            "rationale": "Writing to the clinical record is high-risk and may be irreversible.",
            "evidence_required": ["source_refs", "reviewer_identity"],
        }
    if at == "send_message":
        return {
            "decision": "require_human",
            "risk_tier": "red",
            "required_human_role": "clinician",
            "constraints": ["human_must_approve_before_send", "no_phi_to_external_without_redaction"],
            "rationale": "Outbound patient/clinical messaging crosses a trust boundary.",
            "evidence_required": ["source_refs", "reviewer_identity"],
        }

    # 3. ORANGE --------------------------------------------------------------
    if at == "execute_code":
        return {
            "decision": "require_human",
            "risk_tier": "orange",
            "required_human_role": "technical_steward",
            "constraints": ["blast_radius_estimate_required", "senior_plus_technical_steward_approval"],
            "rationale": "Code execution requires senior + technical steward review.",
            "evidence_required": ["blast_radius_estimate"],
        }
    if f["external_boundary_crossed"] or (at == "call_api" and f["external_action"]):
        return {
            "decision": "require_human",
            "risk_tier": "orange",
            "required_human_role": "senior_clinician",
            "constraints": ["externality_raises_the_floor", "redaction_required_if_phi"],
            "rationale": "Action crosses an external boundary; governance posture is elevated.",
            "evidence_required": ["source_refs"],
        }

    # 4. YELLOW --------------------------------------------------------------
    if f["phi_present"] and at in {"draft", "summarize", "handoff_to_agent"}:
        return {
            "decision": "require_human",
            "risk_tier": "yellow",
            "required_human_role": f.get("requester_role") or "rn",
            "constraints": ["output_must_remain_draft", "must_display_missing_data", "must_include_source_refs"],
            "rationale": "Clinical content with PHI may influence care; human validation required.",
            "evidence_required": ["source_refs"],
        }
    if f["has_clinical_impact"] and at in {"draft", "summarize"}:
        return {
            "decision": "require_human",
            "risk_tier": "yellow",
            "required_human_role": f.get("requester_role") or "rn",
            "constraints": ["output_must_remain_draft", "must_include_source_refs"],
            "rationale": "Clinically relevant draft requires human validation.",
        }

    # 5. GREEN ---------------------------------------------------------------
    if at in {"retrieve", "summarize"}:
        return {
            "decision": "allow_with_constraints",
            "risk_tier": "green",
            "constraints": ["must_cite_source", "no_extrapolation_beyond_source"],
            "rationale": "Bounded, reversible informational task.",
        }
    return {
        "decision": "allow",
        "risk_tier": "green",
        "rationale": "Low-risk, bounded, reversible action.",
    }


class LocalRuleBackend:
    """In-process decision backend. No external dependencies."""

    def evaluate(self, features: dict) -> dict:
        return _decide(features)
