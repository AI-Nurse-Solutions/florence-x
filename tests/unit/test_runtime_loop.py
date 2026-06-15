from florence_core.events import EventLog, NullSink
from florence_core.schemas import RequesterContext, Signal
from florence_core.workflows import (
    AutoApproveReviewer,
    QueueReviewer,
    Runtime,
    load_agent,
    load_workflow,
)
from florence_edena import EdenaClient

WF = "examples/icu_handoff/workflow.yaml"
AG = "examples/icu_handoff/agent.yaml"


def _signal(stype="icu_handoff_needed", dc="phi_local", role="rn"):
    return Signal(signal_id="s", source="test", signal_type=stype,
                  requester=RequesterContext(role=role), data_classification=dc)


def _runtime(reviewer):
    agent = load_agent(AG)
    return Runtime(EdenaClient(), events=EventLog(NullSink()),
                   agents={agent.agent_id: agent}, reviewer=reviewer)


def test_run_completes_with_evidence_after_approval():
    rt = _runtime(AutoApproveReviewer())
    bundle = rt.run(load_workflow(WF), _signal())
    assert bundle.bundle_id
    assert bundle.final_action == "draft"
    assert len(bundle.edena_decisions) == 1
    assert bundle.edena_decisions[0].decision == "require_human"
    assert bundle.edena_decisions[0].risk_tier == "yellow"
    assert bundle.human_reviews and bundle.human_reviews[0].outcome == "approve"
    assert bundle.source_citations  # evidence is never empty


def test_queue_reviewer_pauses_run():
    rt = _runtime(QueueReviewer())
    bundle = rt.run(load_workflow(WF), _signal())
    run = rt.repo.get_run(bundle.workflow_run_id)
    assert run.status == "awaiting_human"
    assert bundle.final_action == "awaiting_human_review"


def test_every_run_emits_an_evidence_bundle():
    rt = _runtime(AutoApproveReviewer())
    bundle = rt.run(load_workflow(WF), _signal())
    assert rt.repo.get_evidence(bundle.bundle_id) is not None
