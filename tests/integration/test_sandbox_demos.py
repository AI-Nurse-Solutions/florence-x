"""Phase 4D: the 5 MVP workflows run through the gateway + connectors with EDENA
gating, local model route only, no PHI leaving local. A2A handoffs are
CandidateActions. Extends the PHI boundary per connector.
"""
import pytest
from florence_connectors.sandbox import build_sandbox_gateway
from florence_core.schemas import CandidateAction
from florence_edena import EdenaClient
from florence_model_router import ModelRouter

BUNDLE = "examples/_fixtures/fhir/synthetic_icu_patient_bundle.json"


def _action(**kw):
    base = {
        'action_id': 'a',
        'workflow_run_id': 'w',
        'agent_id': 'ag',
        'requester_role': 'rn',
        'action_type': 'retrieve',
        'intended_target': 't',
        'data_classification': 'phi_local',
        'reversible': True,
        'external_boundary_crossed': False,
        'proposed_payload_hash': 'h',
    }
    base.update(kw)
    return CandidateAction(**base)


@pytest.fixture
def gw():
    return build_sandbox_gateway(EdenaClient(), BUNDLE)


# (workflow, tool, action_type, data_class, external, expect_executed, expect_reason)
DEMOS = [
    ("icu_handoff", "fhir_read_patient_summary", "retrieve", "phi_local", False, True, None),
    ("patient_education", "education_template_search", "retrieve", "internal", False, True, None),
    ("policy_retrieval", "local_policy_search", "retrieve", "internal", False, True, None),
    ("prior_auth_read", "fhir_read_medications", "retrieve", "phi_local", False, True, None),
    # The consequential prior-auth submission crosses an external boundary -> Orange, gated.
    ("prior_auth_submit", "payer_portal_submit", "call_api", "phi_redacted", True, False,
     "edena_require_human"),
    # Agentic software review: prod code execution is hard-blocked before any tool runs.
    ("agentic_software_review", "code_exec", "execute_code", "internal", False, False, "edena_deny"),
]


@pytest.mark.parametrize("name,tool,atype,dc,ext,executed,reason", DEMOS, ids=[d[0] for d in DEMOS])
def test_workflow_tool_actions_are_governed(gw, name, tool, atype, dc, ext, executed, reason):
    action_id = "run-on-prod" if atype == "execute_code" else "a"
    res = gw.invoke(_action(action_type=atype, data_classification=dc,
                            external_boundary_crossed=ext, tool_requested=tool,
                            reversible=not ext, action_id=action_id))
    assert res.executed is executed
    if executed:
        # Connector returned references only — no raw narrative crossed the boundary.
        refs = res.result.get("resource_ids") or res.result.get("document_refs")
        assert refs and all(":" in r or "/" in r for r in refs)
    else:
        assert res.refused is True and res.reason == reason


def test_phi_work_routes_local_only():
    router = ModelRouter(allow_cloud=True)
    for dc in ("phi_local",):
        route = router.route(workflow_run_id="w", data_classification=dc, risk_tier="yellow")
        assert route.locality.startswith("local")
        assert route.phi_allowed is True


def test_a2a_handoff_is_a_candidate_action(gw):
    # A PHI handoff is Yellow -> require_human: the gateway will not auto-execute it.
    res = gw.invoke(_action(action_type="handoff_to_agent", data_classification="phi_local",
                            tool_requested="handoff_to_agent"))
    assert res.executed is False and res.reason == "edena_require_human"

    # A non-PHI, internal handoff clears EDENA and runs through the A2A connector.
    res2 = gw.invoke(_action(action_type="handoff_to_agent", data_classification="internal",
                             tool_requested="handoff_to_agent"))
    # handoff_to_agent is not a draft/summarize, and internal+reversible -> allow.
    assert res2.executed is True
    assert res2.result["action"] == "handoff_to_agent"
