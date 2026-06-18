"""P1-9 acceptance: a run paused at the human-review interrupt resumes to
completion from a durable checkpoint — including from a brand-new runtime
instance reading the same checkpoint store (the restart property).
"""
import sqlite3

import pytest

pytest.importorskip("langgraph")
pytest.importorskip("langgraph.checkpoint.sqlite")

from langgraph.checkpoint.sqlite import SqliteSaver

from florence_core.events import EventLog, NullSink
from florence_core.schemas import HumanReview, RequesterContext, Signal
from florence_core.schemas.enums import HumanReviewOutcome
from florence_core.state import InMemoryRepository
from florence_core.workflows import QueueReviewer, load_agent, load_workflow
from florence_core.workflows.graph_runtime import GraphRuntime
from florence_edena import EdenaClient

WF = "examples/icu_handoff/workflow.yaml"
AG = "examples/icu_handoff/agent.yaml"
RUN_ID = "wfr_resume_test"


def _signal():
    return Signal(signal_id="s-resume", source="test", signal_type="icu_handoff_needed",
                  requester=RequesterContext(role="rn"), data_classification="phi_local")


def _saver(path):
    saver = SqliteSaver(sqlite3.connect(str(path), check_same_thread=False))
    saver.setup()
    return saver


def test_pause_then_resume_in_memory():
    """QueueReviewer pauses; an explicit approval resumes the same runtime."""
    agent = load_agent(AG)
    rt = GraphRuntime(EdenaClient(), events=EventLog(NullSink()),
                      agents={agent.agent_id: agent}, reviewer=QueueReviewer())
    paused = rt.run(load_workflow(WF), _signal(), run_id=RUN_ID)
    assert paused.final_action == "awaiting_human_review"
    assert rt.repo.get_run(RUN_ID).status == "awaiting_human"

    review = HumanReview(
        review_id="hr_1", action_id=paused.edena_decisions[0].action_id,
        decision_id=paused.edena_decisions[0].decision_id, reviewer_role="rn",
        reviewer_ref="HUMAN", outcome=HumanReviewOutcome.APPROVE)
    done = rt.resume(RUN_ID, review)
    assert done.final_action == "draft"
    assert [r.outcome for r in done.human_reviews] == ["approve"]
    assert rt.repo.get_run(RUN_ID).status == "completed"


def test_resume_from_fresh_runtime_after_restart(tmp_path):
    """The durability property: a NEW GraphRuntime + NEW checkpointer connection on
    the same SQLite file resumes a run paused by a previous instance."""
    db = tmp_path / "checkpoints.db"
    repo = InMemoryRepository()  # shared durable record (Postgres durability is P1-6)
    agent = load_agent(AG)
    agents = {agent.agent_id: agent}

    # Instance 1: start and pause.
    rt1 = GraphRuntime(EdenaClient(), repo=repo, events=EventLog(NullSink()),
                       agents=agents, reviewer=QueueReviewer(), checkpointer=_saver(db))
    paused = rt1.run(load_workflow(WF), _signal(), run_id=RUN_ID)
    assert paused.final_action == "awaiting_human_review"
    del rt1  # simulate process exit

    # Instance 2: fresh runtime + fresh connection to the same checkpoint file.
    rt2 = GraphRuntime(EdenaClient(), repo=repo, events=EventLog(NullSink()),
                       agents=agents, reviewer=QueueReviewer(), checkpointer=_saver(db))
    review = HumanReview(
        review_id="hr_2", action_id=paused.edena_decisions[0].action_id,
        decision_id=paused.edena_decisions[0].decision_id, reviewer_role="rn",
        reviewer_ref="HUMAN", outcome=HumanReviewOutcome.APPROVE)
    done = rt2.resume(RUN_ID, review)

    assert done.final_action == "draft"
    assert [r.outcome for r in done.human_reviews] == ["approve"]
    assert repo.get_run(RUN_ID).status == "completed"


def test_resumed_evidence_records_the_review_on_a_durable_repo(tmp_path):
    """Regression (caught by the live e2e run): with an append-only durable repo,
    the partial pause-bundle must NOT shadow the final bundle — the persisted
    evidence at run.evidence_bundle_id must contain the human review."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.db.models import Base
    from app.db.repository import PostgresRepository

    engine = create_engine(f"sqlite:///{tmp_path / 'durable.db'}", future=True)
    Base.metadata.create_all(engine)
    repo = PostgresRepository(sessionmaker(bind=engine, autoflush=False, expire_on_commit=False))

    agent = load_agent(AG)
    rt = GraphRuntime(EdenaClient(), repo=repo, events=EventLog(NullSink()),
                      agents={agent.agent_id: agent}, reviewer=QueueReviewer(),
                      checkpointer=_saver(tmp_path / "ck.db"))
    paused = rt.run(load_workflow(WF), _signal(), run_id=RUN_ID)
    review = HumanReview(
        review_id="hr_d", action_id=paused.edena_decisions[0].action_id,
        decision_id=paused.edena_decisions[0].decision_id, reviewer_role="rn",
        reviewer_ref="HUMAN", outcome=HumanReviewOutcome.APPROVE)
    rt.resume(RUN_ID, review)

    run = repo.get_run(RUN_ID)
    persisted = repo.get_evidence(run.evidence_bundle_id)
    assert run.status == "completed"
    assert [r.outcome for r in persisted.human_reviews] == ["approve"]
    assert persisted.final_action == "draft"


def test_resume_with_deny_blocks_the_run(tmp_path):
    agent = load_agent(AG)
    rt = GraphRuntime(EdenaClient(), events=EventLog(NullSink()),
                      agents={agent.agent_id: agent}, reviewer=QueueReviewer(),
                      checkpointer=_saver(tmp_path / "deny.db"))
    paused = rt.run(load_workflow(WF), _signal(), run_id=RUN_ID)
    review = HumanReview(
        review_id="hr_3", action_id=paused.edena_decisions[0].action_id,
        decision_id=paused.edena_decisions[0].decision_id, reviewer_role="rn",
        reviewer_ref="HUMAN", outcome=HumanReviewOutcome.DENY)
    done = rt.resume(RUN_ID, review)
    assert done.final_action == "human_deny"
    assert rt.repo.get_run(RUN_ID).status == "blocked"
