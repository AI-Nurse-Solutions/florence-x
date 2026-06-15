"""SqlAlchemyEventSink — append-only persistence of CloudEvents to Postgres (P1-11).

The runtime's EventLog fans every CloudEvent out to its sinks. This sink writes
each event as one immutable row in the ``events`` table (INSERT only, never
UPDATE) — the durable, queryable companion to the JSONL sink. CloudEvent ids are
unique (``evt_<uuid>``), so persistence is naturally idempotent on re-emit.

It lives in apps/api (not florence_core) so the core stays free of a SQLAlchemy
dependency; it satisfies florence_core.events.EventSink structurally.
"""
from __future__ import annotations

from florence_core.events import CloudEvent

from .models import EventRow


class SqlAlchemyEventSink:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def write(self, event: CloudEvent) -> None:
        session = self._session_factory()
        try:
            # Append-only: a row for this event id already existing is a no-op,
            # never an in-place update.
            if session.get(EventRow, event.id) is not None:
                return
            session.add(EventRow(
                id=event.id,
                type=event.type,
                subject=event.subject,
                time=event.time,
                envelope=event.to_dict(),
            ))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
