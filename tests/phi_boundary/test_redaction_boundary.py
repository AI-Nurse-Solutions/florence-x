"""Phase 4B: redaction + the model PHI boundary — PHI never leaves local."""
import pytest
from florence_model_router import (
    ModelRouter,
    OllamaAdapter,
    PhiBoundaryViolation,
    Redactor,
    prepare_prompt,
)

PHI = "Patient Jane Roe, MRN 884521, SSN 555-12-3456, seen 2026-06-15, jane@x.org, 415-555-0199."


def test_redactor_removes_known_patterns_and_is_stable():
    r = Redactor(known_identifiers=["Jane Roe"])
    out = r.redact(PHI)
    for leaked in ["Jane Roe", "884521", "555-12-3456", "2026-06-15", "jane@x.org", "415-555-0199"]:
        assert leaked not in out
    assert not r.contains_phi(out)
    assert r.redact(PHI) == out  # deterministic
    assert "[REDACTED:" in out


def test_local_route_keeps_phi_unchanged_inside_perimeter():
    route = ModelRouter().route(workflow_run_id="w", data_classification="phi_local", risk_tier="yellow")
    assert route.locality.startswith("local")
    # Local stays local — no redaction needed, prompt is unchanged.
    assert prepare_prompt(route, PHI) == PHI


def test_non_local_route_redacts_before_send():
    route = ModelRouter(allow_cloud=True).route(
        workflow_run_id="w", data_classification="phi_redacted", risk_tier="green")
    assert route.locality == "cloud"
    prepared = prepare_prompt(route, PHI, Redactor(known_identifiers=["Jane Roe"]))
    assert "Jane Roe" not in prepared and "555-12-3456" not in prepared


def test_non_local_send_refused_if_phi_survives_redaction():
    route = ModelRouter(allow_cloud=True).route(
        workflow_run_id="w", data_classification="public", risk_tier="green")

    class LeakyRedactor(Redactor):
        def redact(self, text: str) -> str:
            return text  # pretend redaction failed

        def contains_phi(self, text: str) -> bool:
            return True

    with pytest.raises(PhiBoundaryViolation):
        prepare_prompt(route, PHI, LeakyRedactor())


def test_ollama_adapter_is_local_and_parses_response(monkeypatch):
    import florence_model_router.adapters.ollama as mod

    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b'{"response": "drafted summary"}'

    monkeypatch.setattr(mod.urllib.request, "urlopen", lambda *a, **k: FakeResp())
    adapter = OllamaAdapter(model="llama3.1")
    assert adapter.locality.startswith("local")
    assert adapter.generate("hello") == "drafted summary"
