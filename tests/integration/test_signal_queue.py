"""P1-8 acceptance (queue + worker): a signal is accepted, queued, and processed
by the worker into a persisted run + evidence; reserved-but-unacked tasks are
recoverable (restart-safe semantics).
"""
import os

import pytest
from app.config import settings
from app.queue import SignalTask
from app.queue.memory import InMemoryQueue
from app.services.orchestrator import OrchestratorService
from app.worker import process_one
from florence_core.schemas import RequesterContext, Signal


def _signal(signal_id="s-q"):
    return Signal(signal_id=signal_id, source="test", signal_type="icu_handoff_needed",
                  requester=RequesterContext(role="rn"), data_classification="phi_local")


def _task(run_id="wfr_test"):
    return SignalTask(signal=_signal(), workflow_run_id=run_id, auto_approve=True)


# -- reliable-queue semantics ----------------------------------------------
def test_reserve_then_ack_removes_task():
    q = InMemoryQueue()
    q.enqueue(_task("wfr_a"))
    assert q.depth() == 1
    task = q.reserve()
    assert task.workflow_run_id == "wfr_a"
    assert q.depth() == 0
    q.ack(task)
    assert q.recover() == 0  # nothing in-flight after ack


def test_unacked_task_is_recovered():
    """A worker that reserves then crashes (no ack) must not drop the signal."""
    q = InMemoryQueue()
    q.enqueue(_task("wfr_b"))
    q.reserve()                 # reserved, never acked == crashed mid-task
    assert q.depth() == 0
    assert q.recover() == 1     # requeued
    assert q.depth() == 1
    assert q.reserve().workflow_run_id == "wfr_b"


# -- enqueue -> worker -> persisted run + evidence --------------------------
def test_enqueue_then_worker_processes_to_evidence(monkeypatch):
    # This synthetic workflow intentionally uses a simulated reviewer in this test only.
    monkeypatch.setattr(settings, "allow_simulated_review", True)
    orch = OrchestratorService()  # in-memory repo + queue (no DB/Redis configured)

    accepted = orch.enqueue(_signal("s-flow"), auto_approve=True)
    # Run is pollable in PENDING before the worker touches it.
    pending = orch.repo.get_run(accepted.workflow_run_id)
    assert pending is not None and pending.status == "pending"
    assert orch.queue.depth() == 1

    run_id = process_one(orch, orch.queue, timeout=0.1)
    assert run_id == accepted.workflow_run_id

    done = orch.repo.get_run(run_id)
    assert done.status == "completed"
    assert done.evidence_bundle_id is not None
    assert orch.repo.get_evidence(done.evidence_bundle_id) is not None
    assert orch.queue.depth() == 0


def test_worker_idle_returns_none():
    orch = OrchestratorService()
    assert process_one(orch, orch.queue, timeout=0.0) is None


# -- real Redis adapter (gated; needs a broker) -----------------------------
@pytest.mark.skipif(not os.getenv("FLORENCE_TEST_REDIS_URL"),
                    reason="set FLORENCE_TEST_REDIS_URL to run the Redis queue leg")
def test_redis_queue_roundtrip_and_recovery():
    pytest.importorskip("redis")
    from app.queue.redis_queue import RedisQueue

    url = os.environ["FLORENCE_TEST_REDIS_URL"]
    keys = ("florence:test:pending", "florence:test:processing")
    q = RedisQueue(url, pending_key=keys[0], processing_key=keys[1])
    q._r.delete(*keys)  # isolate the test

    q.enqueue(_task("wfr_redis"))
    assert q.depth() == 1
    task = q.reserve(timeout=1.0)
    assert task.workflow_run_id == "wfr_redis"
    assert q.depth() == 0

    # Simulate a crashed worker (no ack) using a fresh client that lost its map.
    q2 = RedisQueue(url, pending_key=keys[0], processing_key=keys[1])
    assert q2.recover() == 1
    assert q2.depth() == 1

    again = q2.reserve(timeout=1.0)
    q2.ack(again)
    assert q2.depth() == 0
    assert q2.recover() == 0
    q2._r.delete(*keys)
