"""LangGraph checkpointer factory (P1-9).

The checkpointer is the durable execution store: with a SQLite/Postgres backend a
paused run survives a process restart and resumes on a HumanReview. Empty config
=> in-memory (process-local) for the MVP and tests.

Graceful: if a backend's optional package isn't installed, fall back to
MemorySaver rather than failing to boot.
"""
from __future__ import annotations

from .config import settings


def make_checkpointer():
    url = settings.langgraph_checkpoint
    if not url:
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()

    if url.startswith("sqlite"):
        try:
            import sqlite3

            from langgraph.checkpoint.sqlite import SqliteSaver

            path = url.split("sqlite:///")[-1] if "sqlite:///" in url else url.split("sqlite://")[-1]
            saver = SqliteSaver(sqlite3.connect(path, check_same_thread=False))
            saver.setup()
            return saver
        except ImportError:
            pass

    if url.startswith("postgres"):
        try:
            from langgraph.checkpoint.postgres import PostgresSaver

            saver = PostgresSaver.from_conn_string(url).__enter__()
            saver.setup()
            return saver
        except ImportError:
            pass

    from langgraph.checkpoint.memory import MemorySaver

    return MemorySaver()
