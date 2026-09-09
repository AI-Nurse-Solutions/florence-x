"""H-002: failure visibility and bounded recovery use synthetic fixtures only."""
from __future__ import annotations

import importlib.util
import json
import logging
import subprocess
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, Mock, call

import pytest
from app.services import orchestrator
from florence_core.dispatcher import Dispatcher
from florence_core.schemas import CandidateAction, RequesterContext, Signal
from florence_edena import EdenaClient
from florence_edena.policy_adapters import opa

ROOT = Path(__file__).resolve().parents[2]
PRIVATE_MARKER = "synthetic-private-marker-not-a-record"


@pytest.mark.parametrize("kind", ["workflow", "agent"])
def test_malformed_example_warns_without_content_and_valid_example_loads(
    tmp_path, monkeypatch, caplog, kind
):
    bad = tmp_path / f"a-{PRIVATE_MARKER}" / f"{kind}.yaml"
    good = tmp_path / "z-valid" / f"{kind}.yaml"
    bad.parent.mkdir()
    good.parent.mkdir()
    bad.write_text(f"invalid: [{PRIVATE_MARKER}", encoding="utf-8")
    good.write_bytes((ROOT / "examples" / "icu_handoff" / f"{kind}.yaml").read_bytes())

    # Real YAML loading and validation; deterministic ordering exercises recovery
    # from the malformed first entry before the valid second entry is loaded.
    original_glob = orchestrator.glob.glob
    monkeypatch.setattr(
        orchestrator.glob, "glob",
        lambda pattern, recursive: sorted(original_glob(pattern, recursive=recursive)),
    )
    service = orchestrator.OrchestratorService.__new__(orchestrator.OrchestratorService)
    service.dispatcher = Dispatcher()
    service.agents = {}
    with caplog.at_level(logging.WARNING, logger="florence.orchestrator"):
        service._load_examples(tmp_path)

    records = [r for r in caplog.records if r.name == "florence.orchestrator"]
    assert len(records) == 1
    assert records[0].getMessage() == f"Skipped an invalid {kind} example during startup"
    assert records[0].exc_info is None
    assert PRIVATE_MARKER not in caplog.text
    assert str(tmp_path) not in caplog.text
    if kind == "agent":
        assert set(service.agents) == {"icu_handoff_synthesizer"}
    else:
        signal = Signal(
            signal_id="synthetic-loader", source="test", signal_type="icu_handoff_needed",
            requester=RequesterContext(role="rn"), data_classification="public",
        )
        assert service.dispatcher.select(signal) is not None


def _backend(monkeypatch, runner):
    monkeypatch.setattr(opa.shutil, "which", lambda name: "/synthetic/opa")
    monkeypatch.setattr(opa.subprocess, "run", runner)
    return opa.OpaBackend("policies/edena")


def test_opa_subprocess_result_is_checked_explicitly(monkeypatch):
    value = {"decision": "require_human", "risk_tier": "yellow"}
    stdout = json.dumps({"result": [{"expressions": [{"value": value}]}]})
    runner = Mock(return_value=subprocess.CompletedProcess(["opa"], 0, stdout=stdout, stderr=""))
    backend = _backend(monkeypatch, runner)
    assert backend.evaluate({"synthetic": True}) == value
    runner.assert_called_once()
    assert runner.call_args.args[0][0:2] == ["opa", "eval"]
    assert runner.call_args.kwargs["check"] is False  # nonzero is converted to RuntimeError
    assert runner.call_args.kwargs["timeout"] == 5
    assert "shell" not in runner.call_args.kwargs
    assert json.loads(runner.call_args.kwargs["input"]) == {"synthetic": True}


@pytest.mark.parametrize("failure", ["nonzero", "timeout"])
@pytest.mark.parametrize("reversible,expected", [(True, "require_human"), (False, "deny")])
def test_opa_process_failure_preserves_fail_closed(monkeypatch, failure, reversible, expected):
    runner = Mock()
    if failure == "nonzero":
        runner.return_value = subprocess.CompletedProcess(["opa"], 1, stdout="", stderr="synthetic error")
    else:
        runner.side_effect = subprocess.TimeoutExpired(["opa"], 5)
    client = EdenaClient(backend=_backend(monkeypatch, runner))
    action = CandidateAction(
        action_id="synthetic-action", workflow_run_id="synthetic-run", agent_id="synthetic-agent",
        requester_role="rn", action_type="draft", intended_target="synthetic-local",
        data_classification="public", reversible=reversible, external_boundary_crossed=False,
        proposed_payload_hash="synthetic-hash",
    )
    result = client.evaluate_action(action)
    assert result.decision == expected
    assert result.rationale.startswith("FAIL-CLOSED:")
    runner.assert_called_once()


@pytest.fixture
def e2e_script():
    spec = importlib.util.spec_from_file_location("florence_e2e_test", ROOT / "scripts" / "e2e_live.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_health_wait_retries_network_error(e2e_script, monkeypatch):
    response = MagicMock()
    response.__enter__.return_value.status = 200
    fetch = Mock(side_effect=[OSError("synthetic connection failure"), response])
    sleep = Mock()
    monkeypatch.setattr(e2e_script.urllib.request, "urlopen", fetch)
    monkeypatch.setattr(e2e_script.time, "sleep", sleep)
    assert e2e_script.wait_for("http://127.0.0.1/synthetic") is True
    assert fetch.call_count == 2
    sleep.assert_called_once_with(0.3)


def test_health_wait_does_not_hide_programming_error(e2e_script, monkeypatch):
    monkeypatch.setattr(
        e2e_script.urllib.request, "urlopen", Mock(side_effect=ValueError("synthetic defect"))
    )
    with pytest.raises(ValueError, match="synthetic defect"):
        e2e_script.wait_for("http://127.0.0.1/synthetic")


def test_e2e_cleanup_kills_and_reaps_timed_out_child(e2e_script, tmp_path, monkeypatch):
    fake_opa = tmp_path / "opa"
    fake_opa.touch()
    monkeypatch.setattr(e2e_script, "OPA", fake_opa)
    slow, stopped = Mock(), Mock()
    slow.wait.side_effect = [subprocess.TimeoutExpired(["synthetic"], 5), 0]
    stopped.wait.return_value = 0
    monkeypatch.setattr(e2e_script.subprocess, "Popen", Mock(side_effect=[slow, stopped]))
    migrate = Mock(return_value=subprocess.CompletedProcess(["synthetic"], 0, stdout="", stderr=""))
    monkeypatch.setattr(e2e_script.subprocess, "run", migrate)
    monkeypatch.setattr(e2e_script, "free_port", Mock(side_effect=[18001, 18002]))
    monkeypatch.setattr(e2e_script, "wait_for", Mock(return_value=True))
    monkeypatch.setattr(e2e_script, "scenario_approve", Mock())
    monkeypatch.setattr(e2e_script, "scenario_deny", Mock())
    rejection = urllib.error.HTTPError("http://127.0.0.1/synthetic", 401, "synthetic rejection", None, None)
    monkeypatch.setattr(e2e_script.urllib.request, "urlopen", Mock(side_effect=rejection))

    assert e2e_script.main() == 0
    slow.terminate.assert_called_once()
    slow.kill.assert_called_once()
    assert slow.wait.call_args_list == [call(timeout=5), call(timeout=5)]
    stopped.terminate.assert_called_once()
    stopped.kill.assert_not_called()
    stopped.wait.assert_called_once_with(timeout=5)
    assert migrate.call_args.kwargs["check"] is False
