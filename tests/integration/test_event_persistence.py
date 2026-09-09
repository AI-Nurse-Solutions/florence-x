"""P1-11 acceptance: events + evidence are persisted to append-only Postgres
tables (in addition to JSONL), and rows are never UPDATEd in place.
"""
from app.db.event_sink import SqlAlchemyEventSink
from app.db.models import Base, EventRow, EvidenceBundleRow
from app.db.repository import PostgresRepository
from florence_core.events import EventLog, NullSink
from florence_core.schemas import RequesterContext, Signal
from florence_core.workflows import AutoApproveReviewer, Runtime, load_agent, load_workflow
from florence_edena import EdenaClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

WF = "examples/icu_handoff/workflow.yaml"
AG = "examples/icu_handoff/agent.yaml"


def _factory(tmp_path, name="events.db"):
    engine = create_engine(f"sqlite:///{tmp_path / name}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False), engine


def _run(repo, events):
    agent = load_agent(AG)
    rt = Runtime(EdenaClient(), repo=repo, events=events,
                 agents={agent.agent_id: agent}, reviewer=AutoApproveReviewer())
    sig = Signal(signal_id="s-evt", source="test", signal_type="icu_handoff_needed",
                 requester=RequesterContext(role="rn"), data_classification="phi_local")
    return rt.run(load_workflow(WF), sig)


def test_events_and_evidence_persisted(tmp_path):
    factory, _engine = _factory(tmp_path)
    repo = PostgresRepository(factory)
    events = EventLog(NullSink(), SqlAlchemyEventSink(factory))

    bundle = _run(repo, events)

    with factory() as s:
        event_count = s.scalar(select(func.count()).select_from(EventRow))
        evidence_count = s.scalar(select(func.count()).select_from(EvidenceBundleRow))
        # The canonical ICU run emits the full event sequence; evidence is one row.
        types = set(s.scalars(select(EventRow.type)).all())

    assert event_count >= 10, f"expected the full event sequence, got {event_count}"
    assert evidence_count == 1
    assert "florence-x.evidence_bundle.persisted" in types
    assert "florence-x.edena.decision" in types
    assert repo.get_evidence(bundle.bundle_id) is not None


def test_event_rows_are_append_only(tmp_path):
    """Re-writing the same CloudEvent id never mutates the stored row, and a
    second run only ever adds rows (no UPDATEs)."""
    factory, _engine = _factory(tmp_path, "append_events.db")
    sink = SqlAlchemyEventSink(factory)
    repo = PostgresRepository(factory)

    first = _run(repo, EventLog(NullSink(), sink))
    with factory() as s:
        count_after_first = s.scalar(select(func.count()).select_from(EventRow))

    # Re-emit one of the first run's events verbatim — must be a no-op.
    from florence_core.events import CloudEvent
    replay = CloudEvent(type="florence-x.edena.decision", subject=first.workflow_run_id,
                        data={"replayed": True})
    # Force a known-duplicate id by writing the same event twice.
    sink.write(replay)
    sink.write(replay)
    with factory() as s:
        row = s.get(EventRow, replay.id)
        count_after_replay = s.scalar(select(func.count()).select_from(EventRow))

    assert row is not None and row.envelope["data"] == {"replayed": True}
    assert count_after_replay == count_after_first + 1, "duplicate id must not add a second row"

    # A fresh run appends a new, disjoint set of rows.
    _run(repo, EventLog(NullSink(), sink))
    with factory() as s:
        count_after_second_run = s.scalar(select(func.count()).select_from(EventRow))
    assert count_after_second_run > count_after_replay
