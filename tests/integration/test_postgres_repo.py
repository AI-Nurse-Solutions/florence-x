"""P1-6 acceptance: PostgresRepository implements the Repository Protocol with
in-memory parity AND survives a process restart.

The default leg uses a persistent temp-file SQLite database so the suite runs
without Docker — the SqlAlchemy code path is identical against Postgres. Set
FLORENCE_TEST_DATABASE_URL=postgresql+psycopg://... to also exercise the
Postgres leg (skipped otherwise).
"""
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base
from app.db.repository import PostgresRepository
from florence_core.events import EventLog, NullSink
from florence_core.schemas import RequesterContext, Signal
from florence_core.state import InMemoryRepository
from florence_core.workflows import AutoApproveReviewer, Runtime, load_agent, load_workflow
from florence_edena import EdenaClient

WF = "examples/icu_handoff/workflow.yaml"
AG = "examples/icu_handoff/agent.yaml"


def _signal(signal_id="s-itg"):
    return Signal(signal_id=signal_id, source="test", signal_type="icu_handoff_needed",
                  requester=RequesterContext(role="rn"), data_classification="phi_local")


def _make_factory(url: str):
    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False), engine


def _run(repo):
    agent = load_agent(AG)
    rt = Runtime(EdenaClient(), repo=repo, events=EventLog(NullSink()),
                 agents={agent.agent_id: agent}, reviewer=AutoApproveReviewer())
    return rt.run(load_workflow(WF), _signal())


@pytest.mark.parametrize("backend", ["sqlite", "postgres"])
def test_run_persists_and_is_retrievable(tmp_path, backend):
    if backend == "postgres" and not os.getenv("FLORENCE_TEST_DATABASE_URL"):
        pytest.skip("set FLORENCE_TEST_DATABASE_URL to run the Postgres leg")
    url = (os.getenv("FLORENCE_TEST_DATABASE_URL") if backend == "postgres"
           else f"sqlite:///{tmp_path / 'florence_test.db'}")
    factory, _engine = _make_factory(url)
    repo = PostgresRepository(factory)

    bundle = _run(repo)

    assert bundle.bundle_id
    assert repo.get_run(bundle.workflow_run_id) is not None
    assert repo.get_evidence(bundle.bundle_id) is not None


def test_in_memory_parity(tmp_path):
    """Same workflow through both backends yields equal reconstructed objects."""
    mem = InMemoryRepository()
    factory, _engine = _make_factory(f"sqlite:///{tmp_path / 'parity.db'}")
    pg = PostgresRepository(factory)

    mem_bundle = _run(mem)
    pg_bundle = _run(pg)

    mem_run = mem.get_run(mem_bundle.workflow_run_id)
    pg_run = pg.get_run(pg_bundle.workflow_run_id)

    # Run IDs differ (fresh uuid per run), but the persisted shape must match.
    assert mem_run.status == pg_run.status
    assert mem_run.workflow_id == pg_run.workflow_id
    assert mem_bundle.final_action == pg_bundle.final_action
    assert [d.risk_tier for d in mem_bundle.edena_decisions] == \
           [d.risk_tier for d in pg_bundle.edena_decisions]
    assert [r.outcome for r in mem_bundle.human_reviews] == \
           [r.outcome for r in pg_bundle.human_reviews]
    # Evidence round-trips losslessly through JSON.
    assert pg.get_evidence(pg_bundle.bundle_id) == pg_bundle


def test_survives_restart(tmp_path):
    """A NEW repository instance (and engine) on the same DB file still sees the
    run and evidence — the durability property P1-6 must guarantee."""
    url = f"sqlite:///{tmp_path / 'restart.db'}"

    factory1, _e1 = _make_factory(url)
    bundle = _run(PostgresRepository(factory1))
    run_id, bundle_id = bundle.workflow_run_id, bundle.bundle_id

    # Simulate a process restart: brand-new engine/session/repository.
    factory2 = sessionmaker(bind=create_engine(url, future=True),
                            autoflush=False, expire_on_commit=False)
    repo2 = PostgresRepository(factory2)

    restored_run = repo2.get_run(run_id)
    restored_evidence = repo2.get_evidence(bundle_id)
    assert restored_run is not None and restored_run.workflow_run_id == run_id
    assert restored_evidence is not None and restored_evidence.bundle_id == bundle_id
    assert restored_evidence == bundle  # full Pydantic equality after reload


def test_list_runs_get_action_and_incidents(tmp_path):
    """P2 repo extensions: query runs by status, fetch an action, persist incidents."""
    from florence_core.schemas import Incident
    from florence_core.schemas.enums import IncidentCategory, IncidentSeverity

    factory, _engine = _make_factory(f"sqlite:///{tmp_path / 'p2.db'}")
    repo = PostgresRepository(factory)
    bundle = _run(repo)

    run = repo.get_run(bundle.workflow_run_id)
    assert run in repo.list_runs()  # equality via reconstructed model
    assert repo.list_runs(status="completed")
    assert repo.list_runs(status="awaiting_human") == []

    action_id = bundle.tool_calls[0].action_id
    assert repo.get_action(action_id) is not None
    assert repo.get_action("act_missing") is None

    assert repo.list_incidents() == []
    inc = Incident(incident_id="inc_1", workflow_run_id=run.workflow_run_id,
                   action_id=action_id, category=IncidentCategory.SAFETY,
                   severity=IncidentSeverity.SEV2, summary="test", triggered_by="human_deny")
    repo.save_incident(inc)
    repo.save_incident(inc)  # append-only: duplicate id is a no-op
    incidents = repo.list_incidents()
    assert len(incidents) == 1 and incidents[0].triggered_by == "human_deny"


def test_evidence_is_append_only(tmp_path):
    """Re-saving the same bundle never mutates the stored row."""
    factory, _engine = _make_factory(f"sqlite:///{tmp_path / 'append.db'}")
    repo = PostgresRepository(factory)
    bundle = _run(repo)

    stored = repo.get_evidence(bundle.bundle_id)
    # A second save of a (hypothetically mutated) bundle with the same id is a no-op.
    mutated = bundle.model_copy(update={"final_action": "TAMPERED"})
    repo.save_evidence(mutated)
    assert repo.get_evidence(bundle.bundle_id).final_action == stored.final_action
