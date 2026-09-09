"""Async signal-intake task queue (P1-8).

`POST /signals` enqueues a SignalTask and returns 202; a worker drains the queue
and runs the governed workflow. Backed by Redis when FLORENCE_REDIS_URL is set
(durable + restart-safe across processes), else an in-process reliable queue for
the MVP and tests.

All backends implement the same reliable-delivery contract:
  enqueue -> reserve (moves to an in-flight set) -> ack (removes it).
A task reserved but never acked (worker crash) is returned to the queue by
recover(), so no accepted signal is silently dropped.
"""
from __future__ import annotations

from typing import Protocol

from florence_core.schemas import Signal
from pydantic import BaseModel


class SignalTask(BaseModel):
    """Unit of work on the queue: a signal + the run it was pre-allocated."""

    model_config = {"extra": "forbid"}

    signal: Signal
    workflow_run_id: str
    auto_approve: bool = False


class SignalAccepted(BaseModel):
    """202 response: the signal was queued and the run is pollable at this id."""

    model_config = {"extra": "forbid"}

    workflow_run_id: str
    signal_id: str
    status: str = "queued"


class TaskQueue(Protocol):
    def enqueue(self, task: SignalTask) -> None: ...
    def reserve(self, timeout: float = 1.0) -> SignalTask | None: ...
    def ack(self, task: SignalTask) -> None: ...
    def recover(self) -> int: ...  # requeue in-flight tasks left by a crashed worker
    def depth(self) -> int: ...


def make_queue() -> TaskQueue:
    """Redis-backed queue when FLORENCE_REDIS_URL is set, else in-process."""
    from ..config import settings

    if settings.redis_url:
        from .redis_queue import RedisQueue

        return RedisQueue(settings.redis_url)
    from .memory import InMemoryQueue

    return InMemoryQueue()
