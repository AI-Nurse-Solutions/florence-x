"""Red team: can a run escape without evidence, or can the audit trail be
tampered with after the fact?

Invariants: every run yields an EvidenceBundle (even when blocked/paused);
events, evidence, and incidents are append-only — a re-save with the same id
never mutates the record. (ASI04 Agentic Supply Chain / audit integrity.)
"""
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.db.event_sink import SqlAlchemyEventSink
from app.db.models import Base, EventRow, EvidenceBundleRow
from app.db.repository import PostgresRepository
from florence_core.events import EventLog, NullSink
from florence_core.schemas import EDENADecision, RequesterContext, Signal
from florence_core.state import InMemoryRepository
from florence_core.workflows import AutoApproveReviewer, Runtime, load_agent, load_workflow
from florence_edena import EdenaClient

WF = "examples/icu_handoff/workflow.yaml"
AG = "examples/icu_handoff/agent.yaml"


def _signal():
    return Signal(signal_id="s", source="test", signal_type="icu_handoff_needed",
                  requester=RequesterContext(role="rn"), data_classification="phi_local")


class _DenyEdena:
    def evaluate_action(self, action) -> EDENADecision:
        return EDENADecision(decision_id="d", action_id=action.action_id,
                             decision="deny", risk_tier="red_blocked", rationale="forced deny")


def _runtime(edena, repo, reviewer=None):
    agent = load_agent(AG)
    return Runtime(edena, repo=repo, events=EventLog(NullSink()),
                   agents={agent.agent_id: agent}, reviewer=reviewer or AutoApproveReviewer())


def test_completed_run_yields_persisted_evidence():
    repo = InMemoryRepository()
    bundle = _runtime(EdenaClient(), repo).run(load_workflow(WF), _signal())
    assert repo.get_evidence(bundle.bundle_id) is not None


def test_denied_run_still_yields_evidence_and_an_incident():
    """A blocked action is a governance success — it must still leave evidence."""
    repo = InMemoryRepository()
    bundle = _runtime(_DenyEdena(), repo).run(load_workflow(WF), _signal())
    assert bundle.final_action and bundle.final_action.startswith("blocked")
    assert repo.get_evidence(bundle.bundle_id) is not None
    assert repo.list_incidents() and repo.list_incidents()[0].triggered_by == "edena_deny"
    # The blocked action never executed a tool.
    assert not any(t.executed for t in bundle.tool_calls)


def _sqlite_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'audit.db'}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def test_evidence_bundle_is_tamper_resistant(tmp_path):
    """ASI04 — re-saving a bundle with the same id but altered content must NOT
    overwrite the original (append-only)."""
    factory = _sqlite_factory(tmp_path)
    repo = PostgresRepository(factory)
    bundle = _runtime(EdenaClient(), repo).run(load_workflow(WF), _signal())
    original = repo.get_evidence(bundle.bundle_id).final_action

    forged = bundle.model_copy(update={"final_action": "TAMPERED", "incident_flags": ["hidden"]})
    repo.save_evidence(forged)
    assert repo.get_evidence(bundle.bundle_id).final_action == original
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(EvidenceBundleRow)) == 1


def test_event_log_is_append_only(tmp_path):
    """ASI04 — a replayed/forged event id cannot add or mutate a second row."""
    factory = _sqlite_factory(tmp_path)
    sink = SqlAlchemyEventSink(factory)
    from florence_core.events import CloudEvent
    evt = CloudEvent(type="florence-x.tool.executed", subject="wfr_x", data={"forged": True})
    sink.write(evt)
    sink.write(evt)  # replay
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(EventRow)) == 1


def test_incident_record_is_append_only(tmp_path):
    factory = _sqlite_factory(tmp_path)
    repo = PostgresRepository(factory)
    from florence_core.schemas import Incident
    from florence_core.schemas.enums import IncidentCategory, IncidentSeverity
    inc = Incident(incident_id="inc_x", category=IncidentCategory.SAFETY,
                   severity=IncidentSeverity.SEV2, summary="real", triggered_by="edena_deny")
    repo.save_incident(inc)
    repo.save_incident(inc.model_copy(update={"summary": "rewritten", "resolved": True}))
    stored = repo.list_incidents()
    assert len(stored) == 1 and stored[0].summary == "real" and stored[0].resolved is False
