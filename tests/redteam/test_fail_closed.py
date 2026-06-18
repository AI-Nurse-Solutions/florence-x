"""Red team: if the governance plane is down or compromised, can anything slip
through as 'allowed'?

Invariant: EDENA fails closed — an unreachable/erroring backend yields a safe,
non-executing decision (deny irreversible/external, else require_human); it NEVER
returns allow. (ASI08 Cascading Failures.)
"""
import pytest

from florence_connectors import FhirReadConnector, ToolGateway
from florence_edena import EdenaClient, EdenaConfig

BUNDLE = "examples/_fixtures/fhir/synthetic_icu_patient_bundle.json"
NON_EXECUTING = {"require_human", "deny", "escalate", "stop", "contain"}

# (action_type, data_class, reversible, external) — a spread of action shapes.
SHAPES = [
    ("retrieve", "internal", True, False),
    ("draft", "phi_local", True, False),
    ("write_record", "phi_local", False, False),
    ("send_message", "phi_local", True, True),
    ("call_api", "internal", True, True),
    ("execute_code", "internal", False, False),
]


class _BoomBackend:
    """A governance backend that is down / compromised."""
    def evaluate(self, features):
        raise RuntimeError("EDENA unavailable / tampered")


@pytest.mark.parametrize("atype,dc,rev,ext", SHAPES)
def test_backend_failure_never_returns_allow(mk_action, atype, dc, rev, ext):
    client = EdenaClient(backend=_BoomBackend())
    d = client.evaluate_action(mk_action(action_type=atype, data_classification=dc,
                                          reversible=rev, external_boundary_crossed=ext))
    assert d.decision in NON_EXECUTING, f"{atype}: fail-open! got {d.decision}"
    assert "FAIL-CLOSED" in d.rationale


def test_irreversible_or_external_is_denied_when_governance_down(mk_action):
    client = EdenaClient(backend=_BoomBackend())
    assert client.evaluate_action(
        mk_action(action_type="write_record", reversible=False)).decision == "deny"
    assert client.evaluate_action(
        mk_action(action_type="call_api", external_boundary_crossed=True)).decision == "deny"


def test_unreachable_opa_server_fails_closed(mk_action):
    """ASI08 — pointing EDENA at a dead OPA server must not allow anything."""
    client = EdenaClient(EdenaConfig(base_url="http://127.0.0.1:1", timeout_s=0.3))
    d = client.evaluate_action(mk_action(action_type="draft", reversible=True))
    assert d.decision == "require_human" and "FAIL-CLOSED" in d.rationale


def test_gateway_does_not_execute_when_governance_is_down(mk_action):
    """Defense in depth: with EDENA down, the gateway refuses to run the tool."""
    gw = ToolGateway(EdenaClient(backend=_BoomBackend()))
    gw.register("fhir_read_patient_summary", FhirReadConnector(BUNDLE), "read_patient_summary")
    res = gw.invoke(mk_action(action_type="retrieve", data_classification="internal",
                              tool_requested="fhir_read_patient_summary"))
    assert res.executed is False and res.refused is True
