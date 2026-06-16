"""Phase 4C: CDS Hooks service + SMART launch — hooks become governed Signals."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from app.main import app
from app.services import get_orchestrator
from florence_connectors.cds_hooks import signal_from_request

HEADERS = {"X-Florence-Identity": "ehr-svc", "X-Florence-Role": "rn"}


@pytest.fixture
def client():
    get_orchestrator.cache_clear()
    with TestClient(app) as c:
        yield c


def test_signal_from_request_carries_hook_context():
    req = {"hook": "patient-view", "hookInstance": "hi-1", "fhirServer": "https://ehr/fhir",
           "context": {"patientId": "Patient/synthetic-icu-001", "userId": "Practitioner/9"}}
    sig = signal_from_request("florence-policy", req, "cds_x")
    assert sig.signal_type == "policy_question"
    assert sig.source == "cds_hooks"
    assert sig.patient_context_present is True
    assert sig.data_classification == "phi_local"
    assert sig.cds_hook_context.hook == "patient-view"


def test_cds_discovery_lists_services(client):
    resp = client.get("/cds-services", headers=HEADERS)
    assert resp.status_code == 200
    ids = {s["id"] for s in resp.json()["services"]}
    assert "florence-patient-education" in ids


def test_cds_invoke_returns_governed_cards(client):
    req = {"hook": "patient-view", "hookInstance": "hi-2",
           "context": {"patientId": "Patient/synthetic-icu-001"}}
    resp = client.post("/cds-services/florence-policy", json=req, headers=HEADERS)
    assert resp.status_code == 200
    cards = resp.json()["cards"]
    assert cards and cards[0]["source"]["label"] == "Florence-X"
    assert cards[0]["indicator"] in {"info", "warning", "critical"}


def test_cds_unknown_service_is_404(client):
    resp = client.post("/cds-services/nope", json={"hook": "patient-view", "context": {}}, headers=HEADERS)
    assert resp.status_code == 404


def test_smart_launch_returns_context(client):
    resp = client.get("/smart/launch?iss=https://ehr/fhir&launch=abc123&patient=Patient/1", headers=HEADERS)
    assert resp.status_code == 200
    ctx = resp.json()
    assert ctx["iss"] == "https://ehr/fhir" and ctx["launch"] == "abc123"
    assert ctx["patient"] == "Patient/1"


def test_smart_launch_requires_iss_and_launch(client):
    resp = client.get("/smart/launch?iss=&launch=", headers=HEADERS)
    assert resp.status_code in (400, 422)
