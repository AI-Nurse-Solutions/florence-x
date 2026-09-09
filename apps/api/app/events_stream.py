"""Live CloudEvents fan-out for the steward console (Phase 3).

An in-process hub broadcasts every emitted CloudEvent to connected WebSocket
clients. The runtime emits synchronously (often from a threadpool worker, since
FastAPI runs sync endpoints off the event loop), so publishing bridges to the
loop with `call_soon_threadsafe`.

Scope: this hub is process-local. The synchronous API path (sync `/signals`,
review resume) streams live here. Cross-process delivery — the P1-8 worker in its
own process — needs a Redis pub/sub relay; that is a documented follow-up (it
requires a broker to exercise) and does not change the `/events/ws` contract.
"""
from __future__ import annotations

import asyncio
import logging

from florence_core.events import CloudEvent

log = logging.getLogger(__name__)


class EventHub:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    def publish(self, event: dict) -> None:
        """Thread-safe: schedule fan-out on the loop. No-op until a client binds
        the loop (live stream has no history; the durable record is the event log).
        Resilient to a closed/stale loop — the live stream must never break a run."""
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        try:
            loop.call_soon_threadsafe(self._fanout, event)
        except RuntimeError:  # loop shutting down between check and schedule
            pass

    def _fanout(self, event: dict) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:  # slow consumer: drop rather than block the loop
                pass


# Process-global hub shared by the EventLog sink and the WebSocket endpoint.
hub = EventHub()


class BroadcastSink:
    """florence_core EventSink that fans CloudEvents to the live hub."""

    def __init__(self, target: EventHub = hub) -> None:
        self._hub = target

    def write(self, event: CloudEvent) -> None:
        # Best-effort live telemetry: a broadcast failure must never break the
        # governed run (the durable record is the JSONL/Postgres event log).
        try:
            self._hub.publish(event.to_dict())
        except Exception:  # noqa: BLE001
            # Do not expose event payloads or exception text in diagnostic logs.
            log.warning("Live event broadcast failed; consult the durable event record")
