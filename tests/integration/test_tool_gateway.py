"""Phase 4A: the ToolGateway enforces EDENA + deny-by-default before any tool runs."""
from florence_connectors import FhirReadConnector, ToolGateway
from florence_core.schemas import CandidateAction
from florence_edena import EdenaClient

BUNDLE = "examples/_fixtures/fhir/synthetic_icu_patient_bundle.json"


def _action(**kw):
    base = {
        'action_id': 'a',
        'workflow_run_id': 'w',
        'agent_id': 'ag',
        'requester_role': 'rn',
        'action_type': 'retrieve',
        'intended_target': 'fhir',
        'data_classification': 'phi_local',
        'reversible': True,
        'external_boundary_crossed': False,
        'proposed_payload_hash': 'h',
        'tool_requested': 'fhir_read_patient_summary',
    }
    base.update(kw)
    return CandidateAction(**base)


def _gateway():
    gw = ToolGateway(EdenaClient())
    gw.register("fhir_read_patient_summary", FhirReadConnector(BUNDLE), "read_patient_summary")
    gw.register("fhir_read_observations", FhirReadConnector(BUNDLE), "read_observations")
    return gw


def test_allowed_action_executes_through_connector():
    # retrieve + internal => green allow_with_constraints
    gw = _gateway()
    res = gw.invoke(_action(data_classification="internal"))
    assert res.executed is True
    assert res.decision == "allow_with_constraints"
    assert res.result and res.result["count"] >= 1
    assert all("/" in r for r in res.result["resource_ids"])  # refs, not narrative


def test_edena_block_prevents_execution():
    # restricted data => deny => never executes
    gw = _gateway()
    res = gw.invoke(_action(data_classification="restricted"))
    assert res.executed is False and res.refused is True
    assert res.decision == "deny"
    assert res.result is None


def test_require_human_is_not_executed_by_the_gateway():
    # PHI draft => require_human (yellow): the gateway does not auto-execute.
    gw = _gateway()
    res = gw.invoke(_action(action_type="draft", data_classification="phi_local",
                            tool_requested="fhir_read_patient_summary"))
    assert res.executed is False and res.refused is True
    assert res.reason == "edena_require_human"


def test_unregistered_tool_is_denied_by_default():
    gw = _gateway()
    res = gw.invoke(_action(data_classification="internal", tool_requested="some_unknown_tool"))
    assert res.executed is False and res.refused is True
    assert res.reason == "tool_not_registered"


def test_fhir_connector_expanded_actions():
    c = FhirReadConnector(BUNDLE)
    assert {"read_allergies", "read_procedures", "read_conditions"} <= set(c.list_actions())
    assert c.invoke("read_allergies", {})["count"] >= 1
    assert c.invoke("read_procedures", {})["count"] >= 1
