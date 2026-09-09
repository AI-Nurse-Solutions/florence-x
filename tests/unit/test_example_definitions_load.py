"""P0-8 gate: every example workflow + agent loads and validates, and every
agent_id referenced by a workflow step has a matching agent.yaml in that example.

This is the acceptance test for BUILD_PLAN.md task P0-8.
"""
from pathlib import Path

import pytest
from florence_core.workflows import load_agent, load_workflow

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"

WORKFLOW_FILES = sorted(EXAMPLES.glob("*/workflow.yaml"))
AGENT_FILES = sorted(EXAMPLES.glob("*/agent.yaml"))


@pytest.mark.parametrize("wf_path", WORKFLOW_FILES, ids=lambda p: p.parent.name)
def test_workflow_validates(wf_path):
    wf = load_workflow(wf_path)
    assert wf.workflow_id
    assert wf.steps


@pytest.mark.parametrize("agent_path", AGENT_FILES, ids=lambda p: p.parent.name)
def test_agent_validates(agent_path):
    agent = load_agent(agent_path)
    assert agent.agent_id
    assert agent.model_route.phi_rule == "never_external_with_phi"


def test_every_referenced_agent_id_has_a_matching_agent_file():
    """Each workflow step's agent_id must resolve to an agent.yaml in the same
    example directory whose agent_id matches exactly."""
    missing = []
    for wf_path in WORKFLOW_FILES:
        wf = load_workflow(wf_path)
        referenced = {s.agent_id for s in wf.steps if s.agent_id}
        agent_path = wf_path.parent / "agent.yaml"
        defined = {load_agent(agent_path).agent_id} if agent_path.exists() else set()
        for agent_id in referenced:
            if agent_id not in defined:
                missing.append(f"{wf_path.parent.name}: step references "
                               f"'{agent_id}' but no matching agent.yaml")
    assert not missing, "Unresolved agent_id references:\n" + "\n".join(missing)


def test_all_five_mvp_examples_have_an_agent():
    have_agent = {p.parent.name for p in AGENT_FILES}
    expected = {
        "icu_handoff",
        "patient_education",
        "policy_retrieval",
        "agentic_software_review",
        "prior_authorization",
    }
    assert expected <= have_agent, f"missing agent.yaml for: {expected - have_agent}"
