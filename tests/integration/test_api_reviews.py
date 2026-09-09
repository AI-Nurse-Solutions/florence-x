"""P2 acceptance: a Yellow+ action pauses, appears in the review queue, resumes to
completion on approval, and a deny blocks the run + creates an Incident.
"""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("langgraph")

from app.main import app
from app.services import get_orchestrator
from app.worker import process_one
from fastapi.testclient import TestClient

HEADERS = {"X-Florence-Identity": "nurse-123", "X-Florence-Role": "rn"}
SIGNAL = {
    "signal_id": "sig-review",
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


def _enqueue_and_drain(client) -> str:
    """Submit a signal (async, QueueReviewer) and let the worker pause it."""
    resp = client.post("/signals", json=SIGNAL, headers=HEADERS)
    assert resp.status_code == 202
    run_id = resp.json()["workflow_run_id"]
    orch = get_orchestrator()
    assert process_one(orch, orch.queue, timeout=0.1) == run_id
    return run_id


def test_paused_run_appears_in_queue_with_context(client):
    run_id = _enqueue_and_drain(client)

    listing = client.get("/reviews", headers=HEADERS)
    assert listing.status_code == 200
    items = listing.json()
    assert any(i["workflow_run_id"] == run_id for i in items)

    item = client.get(f"/reviews/{run_id}", headers=HEADERS).json()
    # Anti-rubber-stamp context must be present, not a bare approve button.
    assert item["risk_tier"] == "yellow"
    assert item["decision"] == "require_human"
    assert item["rationale"]
    assert item["reversible"] is not None
    assert item["source_citations"]


def test_approval_resumes_run_to_completion(client):
    run_id = _enqueue_and_drain(client)
    resp = client.post(f"/reviews/{run_id}", headers=HEADERS,
                       json={"outcome": "approve", "reviewer_ref": "nurse-123"})
    assert resp.status_code == 200
    assert resp.json()["final_action"] == "draft"

    run = client.get(f"/runs/{run_id}", headers=HEADERS).json()
    assert run["status"] == "completed"
    # No longer in the queue.
    assert all(i["workflow_run_id"] != run_id for i in client.get("/reviews", headers=HEADERS).json())


def test_deny_blocks_run_and_creates_incident(client):
    run_id = _enqueue_and_drain(client)
    resp = client.post(f"/reviews/{run_id}", headers=HEADERS,
                       json={"outcome": "deny", "reviewer_ref": "nurse-123", "note": "unsafe"})
    assert resp.status_code == 200
    assert resp.json()["final_action"] == "human_deny"

    run = client.get(f"/runs/{run_id}", headers=HEADERS).json()
    assert run["status"] == "blocked"

    incidents = client.get("/incidents", headers=HEADERS).json()
    mine = [i for i in incidents if i["workflow_run_id"] == run_id]
    assert mine and mine[0]["triggered_by"] == "human_deny"


def test_policy_pack_provenance_is_listed(client):
    resp = client.get("/policy-packs", headers=HEADERS)
    assert resp.status_code == 200
    packs = resp.json()
    pack = next(p for p in packs if p["version"] == "edena-policies-0.1.0")
    assert "yellow" in pack["tiers_covered"] and "red_blocked" in pack["tiers_covered"]
    assert any("decision.rego" in r for r in pack["rego_module_refs"])


def test_review_not_found_is_404(client):
    assert client.get("/reviews/wfr_nope", headers=HEADERS).status_code == 404
    assert client.post("/reviews/wfr_nope", headers=HEADERS,
                       json={"outcome": "approve", "reviewer_ref": "x"}).status_code == 404
