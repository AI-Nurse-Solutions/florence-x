"""In-process reliable queue (MVP / single-process / tests).

Mirrors the reserve/ack/recover contract of RedisQueue so the reliability
semantics are testable without a broker. Not cross-process and not durable across
a real process restart — that property belongs to RedisQueue; this keeps the API
runnable when FLORENCE_REDIS_URL is unset.
"""
from __future__ import annotations

from collections import deque

from . import SignalTask


class InMemoryQueue:
    def __init__(self) -> None:
        self._pending: deque[SignalTask] = deque()
        self._inflight: list[SignalTask] = []

    def enqueue(self, task: SignalTask) -> None:
        self._pending.append(task)

    def reserve(self, timeout: float = 1.0) -> SignalTask | None:
        if not self._pending:
            return None
        task = self._pending.popleft()
        self._inflight.append(task)
        return task

    def ack(self, task: SignalTask) -> None:
        self._inflight = [t for t in self._inflight if t.workflow_run_id != task.workflow_run_id]

    def recover(self) -> int:
        n = len(self._inflight)
        # Return in-flight tasks to the front, preserving order.
        for task in reversed(self._inflight):
            self._pending.appendleft(task)
        self._inflight.clear()
        return n

    def depth(self) -> int:
        return len(self._pending)
