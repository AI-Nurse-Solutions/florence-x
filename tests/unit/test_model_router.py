from florence_model_router import ModelRouter


def test_phi_local_routes_local_only():
    r = ModelRouter(allow_cloud=True).route(
        workflow_run_id="w", data_classification="phi_local", risk_tier="yellow")
    assert r.locality == "local_slm"
    assert r.phi_allowed is True
    assert "local" in r.rationale.lower()


def test_public_task_can_use_cloud_when_enabled():
    r = ModelRouter(allow_cloud=True).route(
        workflow_run_id="w", data_classification="public", risk_tier="green")
    assert r.locality == "cloud"
    assert r.phi_allowed is False


def test_high_risk_forces_local_even_if_non_phi():
    r = ModelRouter(allow_cloud=True).route(
        workflow_run_id="w", data_classification="internal", risk_tier="red")
    assert r.locality == "local_slm"


def test_redacted_requires_redaction_flag():
    r = ModelRouter(allow_cloud=True).route(
        workflow_run_id="w", data_classification="phi_redacted", risk_tier="green")
    assert r.redaction_required is True
