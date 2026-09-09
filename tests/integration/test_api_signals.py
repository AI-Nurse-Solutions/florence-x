"""P1-8 acceptance (API): POST /signals enqueues (202) with a pollable run id;
sync=true runs inline (200 + evidence); Zero Trust denies without identity.
"""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from app.config import settings
from app.main import app
from app.services import get_orchestrator
from app.worker import process_one
from fastapi.testclient import TestClient

HEADERS = {"X-Florence-Identity": "nurse-123", "X-Florence-Role": "rn"}
SIGNAL = {
    "signal_id": "sig-api-1",
    "source": "test",
    "signal_type": "icu_handoff_needed",
    "requester": {"role": "rn"},
    "data_classification": "phi_local",
}


@pytest.fixture
def client():
    # Fresh orchestrator (in-memory repo + queue) for each test.
    get_orchestrator.cache_clear()
    with TestClient(app) as c:
        yield c


def test_missing_identity_is_denied(client):
    resp = client.post("/signals", json=SIGNAL)
    assert resp.status_code == 401


def test_signal_is_accepted_and_run_is_pollable(client):
    resp = client.post("/signals", json=SIGNAL, headers=HEADERS)
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    run_id = body["workflow_run_id"]

    # Pollable immediately, in PENDING (no worker has run yet).
    run = client.get(f"/runs/{run_id}", headers=HEADERS)
    assert run.status_code == 200
    assert run.json()["status"] == "pending"

    # Drain via the same orchestrator the route used, then it completes.
    orch = get_orchestrator()
    assert process_one(orch, orch.queue, timeout=0.1) == run_id
    done = client.get(f"/runs/{run_id}", headers=HEADERS)
    assert done.json()["status"] in {"awaiting_human", "completed"}


def test_sync_mode_returns_evidence_inline(client, monkeypatch):
    # This synthetic test explicitly opts into simulated approval.
    monkeypatch.setattr(settings, "allow_simulated_review", True)
    resp = client.post("/signals?sync=true&auto_approve=true", json=SIGNAL, headers=HEADERS)
    assert resp.status_code == 200
    bundle = resp.json()
    assert bundle["bundle_id"]
    assert bundle["final_action"] == "draft"


def test_unknown_signal_type_is_404(client):
    resp = client.post("/signals", json={**SIGNAL, "signal_type": "no_such_signal"},
                       headers=HEADERS)
    assert resp.status_code == 404


@pytest.mark.parametrize("sync", ["false", "true"])
def test_simulated_approval_is_disabled_by_default(client, monkeypatch, sync):
    monkeypatch.setattr(settings, "allow_simulated_review", False)
    resp = client.post(f"/signals?sync={sync}&auto_approve=true",
                       json=SIGNAL, headers=HEADERS)
    assert resp.status_code == 403
    assert "Simulated review is disabled" in resp.json()["detail"]
