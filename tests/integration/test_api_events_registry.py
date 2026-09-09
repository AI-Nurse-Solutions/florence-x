"""Phase 3 backend (3A): live CloudEvents WebSocket + read-only registry endpoints."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from app.config import settings
from app.main import app
from app.services import get_orchestrator
from fastapi.testclient import TestClient

HEADERS = {"X-Florence-Identity": "nurse-123", "X-Florence-Role": "rn"}
SIGNAL = {
    "signal_id": "sig-ws",
    "source": "test",
    "signal_type": "icu_handoff_needed",
    "requester": {"role": "rn"},
    "data_classification": "phi_local",
}


@pytest.fixture
def client():
    get_orchestrator.cache_clear()
    with TestClient(app) as c:
        yield c


def test_ws_streams_live_cloudevents(client, monkeypatch):
    # This synthetic test explicitly opts into simulated approval.
    monkeypatch.setattr(settings, "allow_simulated_review", True)
    with client.websocket_connect("/events/ws?identity=nurse-123&role=rn") as ws:
        # Trigger a synchronous run; its events should arrive on the socket.
        resp = client.post("/signals?sync=true&auto_approve=true", json=SIGNAL, headers=HEADERS)
        assert resp.status_code == 200
        types = set()
        for _ in range(5):
            evt = ws.receive_json()
            assert evt["source"] == "florence-x"
            types.add(evt["type"])
    assert "florence-x.workflow_run.started" in types


def test_ws_requires_identity(client):
    with pytest.raises(Exception):  # server closes the handshake (1008) without identity
        with client.websocket_connect("/events/ws") as ws:
            ws.receive_json()


def test_agents_registry_lists_registered_agents(client):
    resp = client.get("/agents", headers=HEADERS)
    assert resp.status_code == 200
    agents = resp.json()
    ids = {a["agent_id"] for a in agents}
    assert "icu_handoff_synthesizer" in ids
    icu = next(a for a in agents if a["agent_id"] == "icu_handoff_synthesizer")
    assert icu["institutional_approval_ref"]  # NAIO approval status surfaced
    assert icu["edena_baseline_tier"]


def test_tools_registry_shows_authorization_graph(client):
    resp = client.get("/tools", headers=HEADERS)
    assert resp.status_code == 200
    tools = resp.json()
    by_id = {t["tool_id"]: t for t in tools}
    assert "fhir_read_patient_summary" in by_id
    assert "icu_handoff_synthesizer" in by_id["fhir_read_patient_summary"]["authorized_agents"]
