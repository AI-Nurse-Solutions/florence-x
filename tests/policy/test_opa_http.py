"""P1-12: config-driven EDENA backend selection + HTTP OPA parity.

The toggle and fail-closed tests run everywhere (no OPA needed). The HTTP parity
test boots a local OPA server using the `opa` binary and asserts the server
returns the same decisions as LocalRuleBackend; it skips when `opa` is absent
(same policy as the CLI parity leg in test_parity.py).
"""
import shutil
import socket
import subprocess
import time
import urllib.request

import pytest

from florence_core.schemas import CandidateAction
from florence_edena import EdenaClient, EdenaConfig, make_backend
from florence_edena.policy_adapters.local_rules import LocalRuleBackend
from florence_edena.policy_adapters.opa import OpaHttpBackend
from florence_edena.risk_features import extract_risk_features

CASES = [
    (dict(action_type="retrieve", data_classification="internal"), "allow_with_constraints", "green"),
    (dict(action_type="draft", data_classification="phi_local"), "require_human", "yellow"),
    (dict(action_type="write_record", data_classification="phi_local", reversible=False), "require_human", "red"),
    (dict(action_type="send_message", external_boundary_crossed=True), "require_human", "red"),
    (dict(action_type="call_api", external_boundary_crossed=True), "require_human", "orange"),
    (dict(action_type="execute_code", action_id="run-on-prod", reversible=False), "deny", "red_blocked"),
    (dict(action_type="retrieve", data_classification="restricted"), "deny", "red_blocked"),
]


def _action(**kw):
    base = dict(action_id="a", workflow_run_id="w", agent_id="ag", requester_role="rn",
                action_type="draft", intended_target="t", data_classification="phi_local",
                reversible=True, external_boundary_crossed=False, proposed_payload_hash="h")
    base.update(kw)
    return CandidateAction(**base)


# -- config toggle (no OPA needed) -----------------------------------------
def test_make_backend_defaults_to_local_rules():
    assert isinstance(make_backend(EdenaConfig()), LocalRuleBackend)


def test_make_backend_uses_opa_http_when_base_url_set():
    backend = make_backend(EdenaConfig(base_url="http://opa:8181"))
    assert isinstance(backend, OpaHttpBackend)
    assert backend.url == "http://opa:8181/v1/data/edena/decision"


def test_client_selects_backend_from_config():
    assert isinstance(EdenaClient().backend, LocalRuleBackend)
    assert isinstance(EdenaClient(EdenaConfig(base_url="http://opa:8181")).backend, OpaHttpBackend)


# -- fail-closed on the OPA path (no server reachable) ----------------------
def test_opa_path_fails_closed_when_server_unreachable():
    # Port 1 is never listening; the HTTP call errors and the client must fall
    # back to a safe non-executing decision rather than fail open.
    client = EdenaClient(EdenaConfig(base_url="http://127.0.0.1:1", timeout_s=0.5))
    reversible = client.evaluate_action(_action(action_type="draft", reversible=True))
    assert reversible.decision == "require_human"
    irreversible = client.evaluate_action(
        _action(action_type="write_record", reversible=False))
    assert irreversible.decision == "deny"  # deny irreversible work when governance is down
    assert reversible.rationale.startswith("FAIL-CLOSED")


# -- real HTTP parity against a running OPA server --------------------------
def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def opa_server():
    if shutil.which("opa") is None:
        pytest.skip("opa binary not installed")
    port = _free_port()
    proc = subprocess.Popen(
        ["opa", "run", "--server", "--addr", f"127.0.0.1:{port}", "policies/edena"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(f"{base}/health", timeout=0.5) as r:
                    if r.status == 200:
                        break
            except Exception:  # noqa: BLE001 - server still starting
                time.sleep(0.1)
        else:
            raise RuntimeError("OPA server did not become ready")
        yield base
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.mark.parametrize("kw,decision,tier", CASES)
def test_opa_http_parity(opa_server, kw, decision, tier):
    raw = OpaHttpBackend(opa_server).evaluate(extract_risk_features(_action(**kw)))
    assert raw["decision"] == decision
    assert raw["risk_tier"] == tier
