"""Decision-ladder coverage for the EDENA LocalRuleBackend.

When the `opa` binary is available, this also asserts parity between the Rego
packs (policies/edena) and the Python backend. Otherwise the OPA leg is skipped.
"""
import shutil

import pytest

from florence_core.schemas import CandidateAction
from florence_edena.policy_adapters.local_rules import LocalRuleBackend
from florence_edena.risk_features import extract_risk_features

CASES = [
    (dict(action_type="retrieve", data_classification="internal"), "allow_with_constraints", "green"),
    (dict(action_type="draft", data_classification="phi_local"), "require_human", "yellow"),
    (dict(action_type="write_record", data_classification="phi_local", reversible=False), "require_human", "red"),
    (dict(action_type="send_message", external_boundary_crossed=True), "require_human", "red"),
    (dict(action_type="call_api", external_boundary_crossed=True), "require_human", "orange"),
    (dict(action_type="execute_code", action_id="run-on-prod", reversible=False), "deny", "red_blocked"),
    (dict(action_type="retrieve", data_classification="restricted"), "deny", "red_blocked"),
]


def _action(**kw):
    base = dict(action_id="a", workflow_run_id="w", agent_id="ag", requester_role="rn",
                action_type="draft", intended_target="t", data_classification="phi_local",
                reversible=True, external_boundary_crossed=False, proposed_payload_hash="h")
    base.update(kw)
    return CandidateAction(**base)


@pytest.mark.parametrize("kw,decision,tier", CASES)
def test_local_rule_ladder(kw, decision, tier):
    raw = LocalRuleBackend().evaluate(extract_risk_features(_action(**kw)))
    assert raw["decision"] == decision
    assert raw["risk_tier"] == tier


@pytest.mark.skipif(shutil.which("opa") is None, reason="opa binary not installed")
@pytest.mark.parametrize("kw,decision,tier", CASES)
def test_opa_parity(kw, decision, tier):
    from florence_edena.policy_adapters.opa import OpaBackend

    raw = OpaBackend("policies/edena").evaluate(extract_risk_features(_action(**kw)))
    assert raw["decision"] == decision
    assert raw["risk_tier"] == tier
