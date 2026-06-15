"""PHI boundary: governance objects carry hashes/refs, never raw clinical content."""
from florence_core.events import EventLog, NullSink
from florence_core.schemas import RequesterContext, Signal
from florence_core.workflows import AutoApproveReviewer, Runtime, load_agent, load_workflow
from florence_edena import EdenaClient

SECRET = "Patient Jane Doe MRN 123456 has sepsis"  # would-be raw PHI; must never appear


def test_candidate_action_carries_hash_not_content():
    agent = load_agent("examples/icu_handoff/agent.yaml")
    rt = Runtime(EdenaClient(), events=EventLog(NullSink()),
                 agents={agent.agent_id: agent}, reviewer=AutoApproveReviewer())
    sig = Signal(signal_id="s", source="test", signal_type="icu_handoff_needed",
                 requester=RequesterContext(role="rn"), data_classification="phi_local")
    bundle = rt.run(load_workflow("examples/icu_handoff/workflow.yaml"), sig)
    blob = bundle.model_dump_json()
    assert "proposed_payload_hash" not in blob or SECRET not in blob
    # The evidence bundle stores hashes + source refs, not free-text PHI.
    assert SECRET not in blob


def test_signal_has_no_inline_payload_field():
    sig = Signal(signal_id="s", source="test", signal_type="x",
                 requester=RequesterContext(role="rn"), data_classification="phi_local")
    # Signals reference payloads by pointer; there is no raw-content field.
    assert sig.payload_ref is None
