"""P2 safety: the runtime handles the full EDENA outcome ladder — deny/stop/contain
block (and record an Incident), escalate pauses for a human, throttle proceeds with
constraints. Exercised against both the minimal and the durable runtimes.
"""
import pytest

from florence_core.events import EventLog, NullSink
from florence_core.schemas import EDENADecision, RequesterContext, Signal
from florence_core.state import InMemoryRepository
from florence_core.workflows import AutoApproveReviewer, Runtime, load_agent, load_workflow

WF = "examples/icu_handoff/workflow.yaml"
AG = "examples/icu_handoff/agent.yaml"


class FixedEdena:
    """EDENA stub that returns a chosen decision for every action."""

    def __init__(self, decision: str, tier: str = "red"):
        self._decision, self._tier = decision, tier

    def evaluate_action(self, action) -> EDENADecision:
        return EDENADecision(
            decision_id="dec_fixed", action_id=action.action_id,
            decision=self._decision, risk_tier=self._tier,
            required_human_role="senior_clinician", rationale=f"forced {self._decision}")


def _signal():
    return Signal(signal_id="s", source="test", signal_type="icu_handoff_needed",
                  requester=RequesterContext(role="rn"), data_classification="phi_local")


def _minimal(decision, tier="red"):
    repo = InMemoryRepository()
    agent = load_agent(AG)
    rt = Runtime(FixedEdena(decision, tier), repo=repo, events=EventLog(NullSink()),
                 agents={agent.agent_id: agent}, reviewer=AutoApproveReviewer())
    return rt, repo


def _graph(decision, tier="red"):
    pytest.importorskip("langgraph")
    from florence_core.workflows.graph_runtime import GraphRuntime
    repo = InMemoryRepository()
    agent = load_agent(AG)
    rt = GraphRuntime(FixedEdena(decision, tier), repo=repo, events=EventLog(NullSink()),
                      agents={agent.agent_id: agent}, reviewer=AutoApproveReviewer())
    return rt, repo


@pytest.mark.parametrize("decision", ["deny", "stop", "contain"])
def test_terminal_outcomes_block_and_record_incident_minimal(decision):
    rt, repo = _minimal(decision)
    bundle = rt.run(load_workflow(WF), _signal())
    run = repo.get_run(bundle.workflow_run_id)
    assert run.status in ("blocked", "stopped")
    # The action never executed.
    assert not any(t.executed for t in bundle.tool_calls)
    incidents = repo.list_incidents()
    assert incidents and incidents[0].triggered_by == f"edena_{decision}"
    if decision == "contain":
        assert incidents[0].containment_applied  # containment actions recorded


@pytest.mark.parametrize("decision", ["deny", "stop", "contain"])
def test_terminal_outcomes_block_and_record_incident_graph(decision):
    rt, repo = _graph(decision)
    bundle = rt.run(load_workflow(WF), _signal())
    run = repo.get_run(bundle.workflow_run_id)
    assert run.status in ("blocked", "stopped")
    assert not any(t.executed for t in bundle.tool_calls)
    assert repo.list_incidents()[0].triggered_by == f"edena_{decision}"


def test_escalate_pauses_for_a_human_graph():
    """escalate is a human-required outcome: with QueueReviewer the run pauses."""
    pytest.importorskip("langgraph")
    from florence_core.workflows import QueueReviewer
    from florence_core.workflows.graph_runtime import GraphRuntime
    repo = InMemoryRepository()
    agent = load_agent(AG)
    rt = GraphRuntime(FixedEdena("escalate", "orange"), repo=repo, events=EventLog(NullSink()),
                      agents={agent.agent_id: agent}, reviewer=QueueReviewer())
    bundle = rt.run(load_workflow(WF), _signal(), run_id="wfr_esc")
    assert bundle.final_action == "awaiting_human_review"
    assert repo.get_run("wfr_esc").status == "awaiting_human"
    assert repo.list_incidents() == []  # pausing is not an incident


def test_throttle_proceeds_with_the_action_minimal():
    """throttle is non-terminal: the action proceeds (rate-limiting is a later concern)."""
    rt, repo = _minimal("throttle", tier="green")
    bundle = rt.run(load_workflow(WF), _signal())
    assert any(t.executed for t in bundle.tool_calls)
    assert repo.list_incidents() == []
