"""Red team: can PHI escape the local boundary — to an external model, a
connector payload, or a refused-but-leaked path?

Invariant: PHI never leaves local. Local routes keep PHI inside the perimeter;
non-local routes are redacted and REFUSED if any PHI survives. Connectors return
references, not raw narrative. (ASI06 Memory & Context Poisoning / data leakage.)
"""
import pytest
from florence_connectors import FhirReadConnector
from florence_edena import EdenaClient
from florence_model_router import (
    ModelRouter,
    PhiBoundaryViolation,
    Redactor,
    prepare_prompt,
)

BUNDLE = "examples/_fixtures/fhir/synthetic_icu_patient_bundle.json"

# A battery of identifiers an attacker might smuggle into a prompt.
PHI_SAMPLES = [
    "MRN 884521", "MRN: 00993210", "SSN 555-12-3456", "jane.roe@hospital.org",
    "call 415-555-0199", "DOB 1979-04-02", "seen 3/14/2026", "account 100482311",
]


@pytest.mark.parametrize("sample", PHI_SAMPLES)
def test_redactor_leaves_no_phi_for_external_send(sample):
    r = Redactor(known_identifiers=["Jane Roe"])
    out = r.redact(f"Patient Jane Roe — {sample}.")
    assert "Jane Roe" not in out
    assert not r.contains_phi(out), f"residual PHI after redaction: {out!r}"


def test_non_local_route_refuses_when_phi_survives_redaction():
    """ASI06 — if redaction fails, the boundary must REFUSE the external send,
    never ship the raw text (fail-closed, not best-effort)."""
    route = ModelRouter(allow_cloud=True).route(
        workflow_run_id="w", data_classification="public", risk_tier="green")

    class _LeakyRedactor(Redactor):
        def redact(self, text): return text          # redaction "fails"
        def contains_phi(self, text): return True     # ...and we know it

    with pytest.raises(PhiBoundaryViolation):
        prepare_prompt(route, "Patient Jane Roe, MRN 884521", _LeakyRedactor())


def test_phi_work_is_pinned_to_local_models():
    """Even with cloud enabled, PHI-local work routes local — it can't be sent out."""
    route = ModelRouter(allow_cloud=True).route(
        workflow_run_id="w", data_classification="phi_local", risk_tier="yellow")
    assert route.locality.startswith("local") and route.phi_allowed is True
    # A local route is in-perimeter; prepare_prompt does not externalize it.
    assert prepare_prompt(route, "raw PHI here") == "raw PHI here"


def test_restricted_data_cannot_be_used_in_an_action(mk_action):
    """ASI06 — secrets/credentials (`restricted`) are denied outright."""
    d = EdenaClient().evaluate_action(
        mk_action(action_type="retrieve", data_classification="restricted"))
    assert d.decision == "deny" and d.risk_tier == "red_blocked"


def test_connectors_return_references_not_raw_narrative():
    """A compromised/over-eager prompt can't pull raw clinical text out of a
    connector — only resource refs/codes cross the boundary."""
    c = FhirReadConnector(BUNDLE)
    out = c.invoke("read_patient_summary", {})
    assert set(out) == {"action", "count", "resource_ids"}
    assert all("/" in rid for rid in out["resource_ids"])
    assert "narrative" not in out and "text" not in out
