"""Persistence layer.

Default is florence_core.state.InMemoryRepository. When FLORENCE_DATABASE_URL is
set, make_repository() returns a PostgresRepository (SQLAlchemy) backed by the
same Repository Protocol — runs then survive process restarts. Alembic owns the
schema (see apps/api/alembic + BUILD_PLAN Phase 1, P1-7).
"""
from __future__ import annotations

from florence_core.state import InMemoryRepository, Repository


def make_repository() -> Repository:
    """Return the durable repository if a DB is configured, else in-memory."""
    from .session import SessionLocal

    if SessionLocal is None:
        return InMemoryRepository()
    from .repository import PostgresRepository

    return PostgresRepository(SessionLocal)


def make_event_sinks() -> list:
    """Extra append-only event sinks to add when a DB is configured (P1-11).

    Empty when no DB is set, so the runtime keeps emitting to JSONL only.
    """
    from .session import SessionLocal

    if SessionLocal is None:
        return []
    from .event_sink import SqlAlchemyEventSink

    return [SqlAlchemyEventSink(SessionLocal)]
