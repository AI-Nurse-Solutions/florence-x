"""Redis-backed reliable task queue (P1-8).

Reliability uses the classic two-list pattern:
  * enqueue : LPUSH  pending <json>
  * reserve : BLMOVE pending -> processing (blocking, RIGHT->LEFT) — the task is
              now in-flight and survives an API/worker restart (it lives in Redis).
  * ack     : LREM   processing <json>
  * recover : drain processing back into pending (a worker crashed mid-task), so
              no accepted signal is dropped.

`redis` is imported lazily so the dependency is only required when a Redis URL is
configured (the in-process queue needs nothing).
"""
from __future__ import annotations

from . import SignalTask

_PENDING = "florence:signals:pending"
_PROCESSING = "florence:signals:processing"


class RedisQueue:
    def __init__(self, url: str, *,
                 pending_key: str = _PENDING, processing_key: str = _PROCESSING) -> None:
        import redis  # lazy: only needed when Redis is configured

        self._r = redis.Redis.from_url(url, decode_responses=True)
        self._pending = pending_key
        self._processing = processing_key
        # Maps run_id -> the exact raw payload this process reserved, so ack()
        # removes precisely the right element regardless of serialization drift.
        self._reserved_raw: dict[str, str] = {}

    def enqueue(self, task: SignalTask) -> None:
        self._r.lpush(self._pending, task.model_dump_json())

    def reserve(self, timeout: float = 1.0) -> SignalTask | None:
        # Blocking move keeps the worker idle-cheap; the task lands in processing.
        raw = self._r.blmove(self._pending, self._processing, timeout, "RIGHT", "LEFT")
        if raw is None:
            return None
        task = SignalTask.model_validate_json(raw)
        self._reserved_raw[task.workflow_run_id] = raw
        return task

    def ack(self, task: SignalTask) -> None:
        raw = self._reserved_raw.pop(task.workflow_run_id, task.model_dump_json())
        self._r.lrem(self._processing, 1, raw)

    def recover(self) -> int:
        n = 0
        while self._r.rpoplpush(self._processing, self._pending) is not None:
            n += 1
        return n

    def depth(self) -> int:
        return int(self._r.llen(self._pending))
