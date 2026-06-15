"""P1-9 acceptance: the durable GraphRuntime produces evidence equivalent to the
minimal Runtime across all MVP workflows. Parity is the gate for making `graph`
the default engine (RFC 0007).
"""
from pathlib import Path

import pytest

pytest.importorskip("langgraph")

from florence_core.events import EventLog, NullSink
from florence_core.schemas import RequesterContext, Signal
from florence_core.workflows import AutoApproveReviewer, Runtime, load_agent, load_workflow
from florence_core.workflows.graph_runtime import GraphRuntime
from florence_edena import EdenaClient

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
WORKFLOWS = sorted(p.parent for p in EXAMPLES.glob("*/workflow.yaml")
                   if (p.parent / "agent.yaml").exists())


def _signal(wf):
    return Signal(signal_id="s", source="test", signal_type=wf.signal_types[0],
                  requester=RequesterContext(role="rn"), data_classification="phi_local")


def _fingerprint(bundle):
    """Structural identity of a run's evidence — ignores random ids/timestamps."""
    return {
        "final_action": bundle.final_action,
        "decisions": [(d.decision, d.risk_tier) for d in bundle.edena_decisions],
        "reviews": [r.outcome for r in bundle.human_reviews],
        "sources": sorted(bundle.source_citations),
        "tool_calls": [(t.tool_id, t.executed) for t in bundle.tool_calls],
        "incidents": sorted(bundle.incident_flags),
    }


@pytest.mark.parametrize("wf_dir", WORKFLOWS, ids=lambda p: p.name)
def test_graph_matches_minimal_runner(wf_dir):
    wf = load_workflow(wf_dir / "workflow.yaml")
    agent = load_agent(wf_dir / "agent.yaml")
    agents = {agent.agent_id: agent}

    minimal = Runtime(EdenaClient(), events=EventLog(NullSink()),
                      agents=agents, reviewer=AutoApproveReviewer())
    graph = GraphRuntime(EdenaClient(), events=EventLog(NullSink()),
                         agents=agents, reviewer=AutoApproveReviewer())

    mb = minimal.run(wf, _signal(wf))
    gb = graph.run(wf, _signal(wf))

    assert _fingerprint(gb) == _fingerprint(mb)


def test_all_five_mvp_workflows_covered():
    assert {p.name for p in WORKFLOWS} == {
        "icu_handoff", "patient_education", "policy_retrieval",
        "agentic_software_review", "prior_authorization",
    }
