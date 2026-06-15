"""Signal-intake worker (P1-8).

Drains the task queue and runs each governed workflow. Run as a long-lived
process alongside the API:

    python -m app.worker

It shares the orchestrator's repository and queue, so with Postgres + Redis
configured the API enqueues, the worker processes, and runs survive a restart of
either process. On startup it recovers any in-flight tasks a crashed worker left
behind, so no accepted signal is dropped.
"""
from __future__ import annotations

import logging
import signal as _signal
import sys

from .queue import SignalTask
from .services import get_orchestrator

log = logging.getLogger("florence.worker")


def process_one(orchestrator, queue, timeout: float = 1.0) -> str | None:
    """Reserve and process a single task. Returns the run_id, or None if idle."""
    task: SignalTask | None = queue.reserve(timeout=timeout)
    if task is None:
        return None
    try:
        orchestrator.run_queued(task)
    finally:
        # Ack even on failure: the run is recorded (evidence/incident) and we must
        # not reprocess it. Durable ret/replay is a Phase 2 concern (LangGraph).
        queue.ack(task)
    return task.workflow_run_id


def main() -> int:  # pragma: no cover - process entrypoint
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    orchestrator = get_orchestrator()
    queue = orchestrator.queue

    recovered = queue.recover()
    if recovered:
        log.info("recovered %d in-flight task(s) from a previous run", recovered)

    running = {"on": True}

    def _stop(*_a):
        running["on"] = False

    _signal.signal(_signal.SIGINT, _stop)
    _signal.signal(_signal.SIGTERM, _stop)

    log.info("worker started; draining queue (depth=%d)", queue.depth())
    while running["on"]:
        run_id = process_one(orchestrator, queue, timeout=2.0)
        if run_id:
            log.info("processed run %s", run_id)
    log.info("worker stopped")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
