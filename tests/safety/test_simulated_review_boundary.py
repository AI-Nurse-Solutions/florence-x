"""Unit/handler checks for server-controlled simulated review.

Collaborators are mocked deliberately. These checks do not establish runtime,
policy, persistence, transport authentication, or end-to-end safety.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from app.config import Settings, SimulatedReviewDisabled, settings
from app.routes import signals
from app.services import orchestrator as orchestrator_module
from app.services.orchestrator import OrchestratorService
from fastapi import HTTPException, Response


@pytest.fixture(autouse=True)
def simulation_disabled(monkeypatch):
    monkeypatch.setattr(settings, "allow_simulated_review", False)


@pytest.fixture
def service():
    instance = OrchestratorService.__new__(OrchestratorService)
    instance._select = Mock(return_value=SimpleNamespace(workflow_id="synthetic-workflow"))
    instance.repo = Mock()
    instance.queue = Mock()
    instance.dispatcher = Mock()
    instance.events = Mock()
    instance.agents = {}
    instance._edena = Mock()
    instance.runtime_kind = "graph"
    instance._graph_runtime = Mock()
    return instance


@pytest.mark.parametrize("value,enabled", [
    (None, False), ("", False), ("false", False), ("FALSE", False),
    ("0", False), ("1", False), ("yes", False), ("on", False),
    ("unexpected", False), ("true", True), ("TRUE", True), (" true ", True),
])
def test_server_opt_in_parser(monkeypatch, value, enabled):
    if value is None:
        monkeypatch.delenv("FLORENCE_ALLOW_SIMULATED_REVIEW", raising=False)
    else:
        monkeypatch.setenv("FLORENCE_ALLOW_SIMULATED_REVIEW", value)
    assert Settings().allow_simulated_review is enabled


@pytest.mark.parametrize("value", [False, None, "true", "false", 1])
def test_non_boolean_programmatic_opt_in_is_not_permission(value):
    config = Settings(allow_simulated_review=value)
    with pytest.raises(SimulatedReviewDisabled):
        config.check_auto_approval(True)


def test_explicit_opt_in_allows_simulation():
    Settings(allow_simulated_review=True).check_auto_approval(True)


def test_normal_review_remains_available():
    Settings(allow_simulated_review=False).check_auto_approval(False)


@pytest.mark.parametrize("method", ["submit", "enqueue"])
def test_direct_service_rejects_before_side_effects(service, method):
    service._runtime_for = Mock()
    with pytest.raises(SimulatedReviewDisabled):
        getattr(service, method)(SimpleNamespace(signal_id="synthetic"), auto_approve=True)
    service._select.assert_not_called()
    service._runtime_for.assert_not_called()
    assert service.repo.mock_calls == []
    assert service.queue.mock_calls == []


@pytest.mark.parametrize("runtime_kind", ["graph", "minimal"])
def test_factory_rechecks_before_constructing_reviewer(service, monkeypatch, runtime_kind):
    service.runtime_kind = runtime_kind
    auto = Mock()
    monkeypatch.setattr(orchestrator_module, "AutoApproveReviewer", auto)
    with pytest.raises(SimulatedReviewDisabled):
        service._runtime_for(True)
    auto.assert_not_called()
    service._graph_runtime.assert_not_called()


@pytest.mark.parametrize("auto_approve", [False, True])
def test_explicit_demo_uses_requested_reviewer(service, monkeypatch, auto_approve):
    monkeypatch.setattr(settings, "allow_simulated_review", True)
    service._runtime_for(auto_approve)
    reviewer = service._graph_runtime.call_args.args[0]
    expected = (orchestrator_module.AutoApproveReviewer if auto_approve
                else orchestrator_module.QueueReviewer)
    assert isinstance(reviewer, expected)


def test_default_factory_uses_queue_reviewer(service):
    service._runtime_for(False)
    assert isinstance(service._graph_runtime.call_args.args[0],
                      orchestrator_module.QueueReviewer)


def test_normal_sync_submission_is_unchanged(service):
    runtime = Mock()
    service._runtime_for = Mock(return_value=runtime)
    signal = SimpleNamespace(signal_id="synthetic")
    assert service.submit(signal) is runtime.run.return_value
    service._runtime_for.assert_called_once_with(False)
    runtime.run.assert_called_once_with(service._select.return_value, signal)


@pytest.mark.parametrize("worker_opt_in", [False, True])
def test_queued_request_rechecks_worker_config(service, monkeypatch, caplog, worker_opt_in):
    monkeypatch.setattr(settings, "allow_simulated_review", worker_opt_in)
    runtime = Mock()
    service._runtime_for = Mock(return_value=runtime)
    signal = SimpleNamespace(signal_id="synthetic")
    task = SimpleNamespace(signal=signal, auto_approve=True, workflow_run_id="wfr_synthetic")
    assert service.run_queued(task) is runtime.run.return_value
    service._runtime_for.assert_called_once_with(worker_opt_in)
    runtime.run.assert_called_once_with(service._select.return_value, signal, run_id="wfr_synthetic")
    assert task.auto_approve is True  # Do not rewrite the original request/history.
    if not worker_opt_in:
        assert "using policy-required human review" in caplog.text
    else:
        assert "Simulated review disabled" not in caplog.text


@pytest.mark.parametrize("sync", [False, True])
def test_handler_rejects_before_obtaining_orchestrator(monkeypatch, sync):
    get_service = Mock()
    monkeypatch.setattr(signals, "get_orchestrator", get_service)
    with pytest.raises(HTTPException) as exc:
        signals.submit_signal(SimpleNamespace(signal_id="synthetic"), Response(),
                              sync=sync, auto_approve=True)
    assert exc.value.status_code == 403
    assert "Simulated review is disabled" in exc.value.detail
    get_service.assert_not_called()


@pytest.mark.parametrize("sync,expected_status", [(False, 202), (True, 200)])
def test_handler_preserves_normal_status(monkeypatch, sync, expected_status):
    service = Mock()
    monkeypatch.setattr(signals, "get_orchestrator", Mock(return_value=service))
    response = Response(status_code=202)
    result = signals.submit_signal(SimpleNamespace(signal_id="synthetic"), response,
                                   sync=sync, auto_approve=False)
    expected = service.submit if sync else service.enqueue
    assert result is expected.return_value
    assert response.status_code == expected_status


def test_handler_preserves_missing_workflow_error(monkeypatch):
    service = Mock()
    service.enqueue.side_effect = KeyError("missing synthetic workflow")
    monkeypatch.setattr(signals, "get_orchestrator", Mock(return_value=service))
    with pytest.raises(HTTPException) as exc:
        signals.submit_signal(SimpleNamespace(signal_id="synthetic"), Response(),
                              sync=False, auto_approve=False)
    assert exc.value.status_code == 404


def test_handler_maps_service_recheck_to_403(monkeypatch):
    # The handler's initial check succeeds; the service performs a later recheck.
    monkeypatch.setattr(settings, "allow_simulated_review", True)
    service = Mock()
    service.submit.side_effect = SimulatedReviewDisabled("Simulated review is disabled")
    monkeypatch.setattr(signals, "get_orchestrator", Mock(return_value=service))
    with pytest.raises(HTTPException) as exc:
        signals.submit_signal(SimpleNamespace(signal_id="synthetic"), Response(),
                              sync=True, auto_approve=True)
    assert exc.value.status_code == 403
