from florence_core.schemas import CandidateAction
from florence_edena import EdenaClient


def _action(**kw):
    base = {
        'action_id': 'a',
        'workflow_run_id': 'w',
        'agent_id': 'ag',
        'requester_role': 'rn',
        'action_type': 'draft',
        'intended_target': 't',
        'data_classification': 'phi_local',
        'reversible': True,
        'external_boundary_crossed': False,
        'proposed_payload_hash': 'h',
    }
    base.update(kw)
    return CandidateAction(**base)


def test_restricted_data_is_denied():
    d = EdenaClient().evaluate_action(_action(action_type="retrieve", data_classification="restricted"))
    assert d.decision == "deny"
    assert d.risk_tier == "red_blocked"


def test_production_code_execution_is_blocked():
    d = EdenaClient().evaluate_action(_action(action_type="execute_code", action_id="deploy-to-prod",
                                              reversible=False))
    assert d.decision == "deny"
    assert d.risk_tier == "red_blocked"


def test_ehr_write_requires_human():
    d = EdenaClient().evaluate_action(_action(action_type="write_record", reversible=False))
    assert d.decision == "require_human"
    assert d.risk_tier == "red"


def test_fail_closed_when_backend_errors():
    class Boom:
        def evaluate(self, f):
            raise RuntimeError("edena unavailable")

    d = EdenaClient(backend=Boom()).evaluate_action(
        _action(action_type="send_message", reversible=False, external_boundary_crossed=True)
    )
    # Irreversible + external => deny, never allow.
    assert d.decision == "deny"
    assert "FAIL-CLOSED" in d.rationale
