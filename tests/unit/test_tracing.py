"""P1-10 acceptance: the runtime loop, the EDENA call, and tool execution emit
OpenTelemetry spans with per-step latency recorded.

Uses an in-memory span exporter (no collector needed). Skips if the OTel SDK is
not installed; the runtime falls back to no-op spans in that case.
"""
import pytest

pytest.importorskip("opentelemetry.sdk")

from florence_core.events import EventLog, NullSink
from florence_core.schemas import RequesterContext, Signal
from florence_core.workflows import AutoApproveReviewer, Runtime, load_agent, load_workflow
from florence_edena import EdenaClient
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

WF = "examples/icu_handoff/workflow.yaml"
AG = "examples/icu_handoff/agent.yaml"


_EXPORTER = InMemorySpanExporter()


@pytest.fixture(scope="session", autouse=True)
def _otel_provider():
    # The global TracerProvider may only be set once per process, so install a
    # single shared in-memory exporter for the whole session.
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(_EXPORTER))
    trace.set_tracer_provider(provider)
    yield


@pytest.fixture
def spans(_otel_provider):
    _EXPORTER.clear()
    yield _EXPORTER
    _EXPORTER.clear()


def _run():
    agent = load_agent(AG)
    rt = Runtime(EdenaClient(), events=EventLog(NullSink()),
                 agents={agent.agent_id: agent}, reviewer=AutoApproveReviewer())
    sig = Signal(signal_id="s-otel", source="test", signal_type="icu_handoff_needed",
                 requester=RequesterContext(role="rn"), data_classification="phi_local")
    return rt.run(load_workflow(WF), sig)


def test_runtime_emits_expected_spans(spans):
    _run()
    finished = spans.get_finished_spans()
    names = {s.name for s in finished}

    assert {"florence.workflow_run", "florence.workflow_step",
            "florence.edena.evaluate", "florence.tool.execute"} <= names


def test_run_span_records_latency_and_attributes(spans):
    _run()
    by_name = {s.name: s for s in spans.get_finished_spans()}

    run_span = by_name["florence.workflow_run"]
    assert run_span.end_time > run_span.start_time  # latency recorded
    assert run_span.attributes["workflow_id"] == "icu_shift_handoff"
    assert run_span.attributes["status"] == "completed"
    assert run_span.attributes["final_action"] == "draft"


def test_edena_span_records_decision(spans):
    _run()
    by_name = {s.name: s for s in spans.get_finished_spans()}
    edena_span = by_name["florence.edena.evaluate"]
    assert edena_span.attributes["edena.decision"] == "require_human"
    assert edena_span.attributes["edena.risk_tier"] == "yellow"


def test_step_spans_have_duration(spans):
    _run()
    step_spans = [s for s in spans.get_finished_spans() if s.name == "florence.workflow_step"]
    assert step_spans, "expected per-step spans"
    assert all(s.end_time >= s.start_time for s in step_spans)
