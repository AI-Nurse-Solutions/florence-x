"""Optional telemetry failures stay visible without exposing exception payloads."""
import logging
from unittest.mock import Mock

from app.events_stream import BroadcastSink
from florence_core.observability import LatencyBudget
from florence_core.observability import tracing as tracing_module
from opentelemetry import trace


def test_broadcast_failure_warns_without_leaking_payload(caplog):
    target = Mock()
    target.publish.side_effect = RuntimeError("synthetic-private-marker")
    event = Mock()
    event.to_dict.return_value = {"detail": "synthetic-private-marker"}
    with caplog.at_level(logging.WARNING, logger="app.events_stream"):
        BroadcastSink(target).write(event)
    assert "Live event broadcast failed" in caplog.text
    assert "synthetic-private-marker" not in caplog.text


def test_latency_failure_warns_without_breaking_workflow(monkeypatch, caplog):
    monkeypatch.setattr(tracing_module, "HAVE_OTEL", True)
    monkeypatch.setattr(trace, "get_current_span", Mock(side_effect=RuntimeError("synthetic-private-marker")))
    with (
        caplog.at_level(logging.WARNING, logger="florence_core.observability.latency"),
        LatencyBudget() as budget,
    ):
        assert budget.elapsed_ms is None
    assert budget.elapsed_ms is not None
    assert "Latency span annotation failed" in caplog.text
    assert "synthetic-private-marker" not in caplog.text
