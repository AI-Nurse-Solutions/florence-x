"""Phase 4E: point-of-care latency budget — a governed run completes within ≤2–3s."""
import time

from florence_core.events import EventLog, NullSink
from florence_core.observability import POINT_OF_CARE_BUDGET_MS, LatencyBudget
from florence_core.schemas import RequesterContext, Signal
from florence_core.workflows import AutoApproveReviewer, Runtime, load_agent, load_workflow
from florence_edena import EdenaClient

WF = "examples/icu_handoff/workflow.yaml"
AG = "examples/icu_handoff/agent.yaml"


def test_budget_reports_elapsed_and_within():
    with LatencyBudget(POINT_OF_CARE_BUDGET_MS) as budget:
        pass
    assert budget.elapsed_ms is not None
    assert budget.within_budget
    assert budget.overage_ms == 0.0


def test_zero_budget_is_exceeded():
    with LatencyBudget(budget_ms=0) as budget:
        time.sleep(0.001)
    assert not budget.within_budget
    assert budget.overage_ms > 0


def test_icu_handoff_run_is_within_point_of_care_budget():
    agent = load_agent(AG)
    rt = Runtime(EdenaClient(), events=EventLog(NullSink()),
                 agents={agent.agent_id: agent}, reviewer=AutoApproveReviewer())
    sig = Signal(signal_id="s", source="t", signal_type="icu_handoff_needed",
                 requester=RequesterContext(role="rn"), data_classification="phi_local")
    with LatencyBudget(POINT_OF_CARE_BUDGET_MS) as budget:
        bundle = rt.run(load_workflow(WF), sig)
    assert bundle.final_action == "draft"
    assert budget.within_budget, f"run took {budget.elapsed_ms:.1f}ms (budget {POINT_OF_CARE_BUDGET_MS}ms)"
