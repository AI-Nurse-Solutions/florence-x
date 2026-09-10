"""SS-05A contract/admission/normalization tests. No live models or network clients."""
from __future__ import annotations

import importlib.util
import json
import socket
from datetime import timedelta
from pathlib import Path

import pytest
from florence_core.schemas.inference import (
    ERROR,
    InferenceRequest,
    fingerprint,
    parse_record,
)
from florence_model_router import ModelRouter
from florence_model_router.inference import plan_inference, replay_inference
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("model_demo", ROOT / "scripts/model_contract_demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


@pytest.fixture
def setup():
    requests, profiles = demo.demo_inputs()
    request = requests[0]
    return request, profiles, demo.fixture_admission(request, profiles)


def change(record, **updates):
    return type(record).model_validate({**record.model_dump(), **updates})


def test_normalized_cross_adapter_report_is_deterministic():
    assert demo.evaluate() == demo.evaluate()
    assert len(demo.evaluate()["tasks"]) == 3
    assert demo.evaluate()["real_model_calls"] == 0


@pytest.mark.parametrize("index", [0, 1, 2])
def test_two_formats_same_request_same_proposal(index):
    requests, profiles = demo.demo_inputs()
    req = requests[index]
    original = req.model_dump_json()
    outputs = []
    for p in profiles:
        reads = demo.ReadTrace(demo.fixture_wires(req))
        result = replay_inference(req, profiles, demo.fixture_admission(req, (p,)), reads, now=demo.NOW)
        assert reads.reads == [p.profile_id]
        assert result.outcome == "proposal_ready"
        assert result.next_action == "human_review"
        assert result.actual_execution == "in_memory_fixture"
        assert result.request_sha256 == fingerprint(req)
        assert result.mission_sha256 == req.mission_sha256
        assert result.authority == "no_execution_permission"
        outputs.append(result.proposal)
    assert outputs[0] == outputs[1]
    assert req.model_dump_json() == original


@pytest.mark.parametrize("field,value", [
    ("data_classification", "internal"), ("data_classification", "phi_local"),
    ("data_classification", "phi_redacted"), ("data_classification", "unknown"),
    ("execution_mode", "live"), ("purpose", "clinical_execution"),
    ("output_contract", "arbitrary"), ("max_output_tokens", True),
    ("max_output_tokens", "100"), ("max_output_tokens", 0),
    ("max_output_bytes", -1), ("timeout_ms", 0),
    ("private_reflection", "PRIVATE_SENTINEL"), ("api_key", "PRIVATE_SENTINEL"),
    ("messages", [{"role": "system", "content": "PRIVATE_SENTINEL"}]),
    ("tools", ["shell"]), ("endpoint", "https://example.invalid"),
])
def test_disallowed_request_fields_refused_without_content_in_error(setup, field, value):
    req, _, _ = setup
    data = req.model_dump(mode="json")
    data[field] = value
    with pytest.raises(ValueError) as exc:
        parse_record(json.dumps(data).encode(), InferenceRequest)
    assert str(exc.value) == ERROR
    assert "PRIVATE_SENTINEL" not in str(exc.value)


@pytest.mark.parametrize("raw", [b'', b'{', b'null', b'[]', b'{"a":NaN}', b'{"a":1,"a":2}',
                                 b'x' * 65537, b'\xff', bytearray(b'{}')])
def test_bounded_unambiguous_json_required(raw):
    with pytest.raises(ValueError, match="Invalid offline inference"):
        parse_record(raw, InferenceRequest)


@pytest.mark.parametrize("mutation", ["quote", "source_hash", "classification", "duplicate_passage"])
def test_context_integrity_and_scope_preserved(setup, mutation):
    req, _, _ = setup
    data = req.model_dump(mode="json")
    if mutation == "quote":
        data["context"][0]["excerpt"] += " altered"
    elif mutation == "source_hash":
        data["context"][0]["source"]["content_sha256"] = "0" * 64
    elif mutation == "classification":
        data["context"][0]["source"]["data_classification"] = "internal"
    else:
        data["context"].append(data["context"][0])
    with pytest.raises(ValueError):
        parse_record(json.dumps(data).encode(), InferenceRequest)


@pytest.mark.parametrize("which", ["missing", "denied", "expired", "future", "changed_request",
                                    "changed_profile", "unknown_destination", "no_identity_match"])
def test_denial_before_response_access(setup, which):
    req, profiles, adm = setup
    if which == "missing":
        adm = None
    elif which == "denied":
        adm = change(adm, disposition="deny")
    elif which == "expired":
        adm = change(adm, valid_from=demo.NOW-timedelta(hours=2), expires_at=demo.NOW)
    elif which == "future":
        adm = change(adm, valid_from=demo.NOW+timedelta(seconds=1))
    elif which == "changed_request":
        req = change(req, task=req.task + " changed")
    elif which == "changed_profile":
        profiles = tuple(change(p, version="0.1.1") for p in profiles)
    elif which == "unknown_destination":
        adm = change(adm, destinations=("personal_cloud",))
    else:
        adm = change(adm, profile_sha256s=("0"*64,))
    trace = demo.ReadTrace(demo.fixture_wires(req))
    result = replay_inference(req, profiles, adm, trace, now=demo.NOW)
    assert result.outcome == "denied" and result.attempts == 0
    assert not trace.reads


@pytest.mark.parametrize("bad", [True, 0, 2, "1", None])
def test_attempt_count_is_exact_strict_one(setup, bad):
    _, _, adm = setup
    with pytest.raises(ValidationError):
        change(adm, max_attempts=bad)


def test_time_requires_timezone(setup):
    req, profiles, adm = setup
    p = plan_inference(req, profiles, adm, now=demo.NOW.replace(tzinfo=None))
    assert p.status == "denied" and p.reason == "invalid_admission"


@pytest.mark.parametrize("payload", [None, {"disposition": "allow_fixture"}])
def test_untyped_admission_is_not_a_permission(setup, payload):
    req, profiles, _ = setup
    assert plan_inference(req, profiles, payload, now=demo.NOW).status == "denied"


def test_legacy_cloud_flag_cannot_grant_admission(setup):
    req, profiles, _ = setup
    assert ModelRouter(allow_cloud=True).plan_inference(req, profiles, None, now=demo.NOW).status == "denied"


def test_destination_precedes_cost_ranking(setup):
    req, profiles, _ = setup
    assert profiles[1].cost_units < profiles[0].cost_units
    adm = demo.fixture_admission(req, profiles, ("device",))
    plan = ModelRouter(allow_cloud=True).plan_inference(req, profiles, adm, now=demo.NOW)
    assert plan.selected_profile == profiles[0]
    assert plan.automatic_fallback == "disabled"


def test_explicit_selection_is_not_silently_replaced(setup):
    req, profiles, _ = setup
    req = change(req, requested_profile="not.in.registry")
    adm = demo.fixture_admission(req, profiles)
    assert plan_inference(req, profiles, adm, now=demo.NOW).status == "denied"


@pytest.mark.parametrize("update", [
    {"capabilities": ("text",)}, {"max_context_bytes": 1}, {"max_output_tokens": 10},
    {"suitability": "not_evaluated"}, {"cost_units": 11}, {"latency_ms": 1001},
])
def test_capability_and_budget_before_selection(setup, update):
    req, profiles, _ = setup
    candidate = change(profiles[0], **update)
    adm = demo.fixture_admission(req, (candidate,))
    assert plan_inference(req, (candidate,), adm, now=demo.NOW).status == "denied"


@pytest.mark.parametrize("feature", ["tool_proposals", "image_input", "streaming"])
def test_unsupported_feature_not_silently_downgraded(setup, feature):
    req, profiles, _ = setup
    req = change(req, required_features=("structured_output", feature))
    adm = demo.fixture_admission(req, profiles)
    assert plan_inference(req, profiles, adm, now=demo.NOW).status == "denied"


@pytest.mark.parametrize("field,value", [("actual_execution", "https://example.invalid"),
                                         ("adapter", "ollama"), ("cost_units", True)])
def test_live_profile_not_accepted(setup, field, value):
    _, profiles, _ = setup
    with pytest.raises(ValidationError):
        change(profiles[0], **{field: value})


def test_duplicate_profile_identity_denied(setup):
    req, profiles, adm = setup
    assert plan_inference(req, (profiles[0], profiles[0]), adm, now=demo.NOW).reason == "invalid_catalog"


@pytest.mark.parametrize("status", ["refused", "timed_out", "cancelled", "unavailable"])
def test_non_success_never_falls_back(setup, status):
    req, profiles, adm = setup
    trace = demo.ReadTrace(demo.fixture_wires(req, status))
    result = replay_inference(req, profiles, adm, trace, now=demo.NOW)
    assert result.outcome == status and result.attempts == 1
    assert result.proposal is None and result.next_action == "stop_no_fallback"
    assert trace.reads == [profiles[1].profile_id]  # Other eligible model never read.


def test_missing_selected_response_does_not_use_another_adapter(setup):
    req, profiles, adm = setup
    trace = demo.ReadTrace({profiles[0].profile_id: demo.fixture_wires(req)[profiles[0].profile_id]})
    result = replay_inference(req, profiles, adm, trace, now=demo.NOW)
    assert result.outcome == "unavailable" and trace.reads == [profiles[1].profile_id]


@pytest.mark.parametrize("mutation", ["malformed", "tool", "status", "empty", "unknown_source", "duplicate_source",
                                       "wrong_usage", "false_verified", "unknown_field", "refusal_with_payload"])
def test_bad_response_quarantined_without_second_attempt(setup, mutation):
    req, profiles, adm = setup
    payload = json.loads(demo.fixture_wires(req)[profiles[1].profile_id])
    if mutation == "tool":
        payload["tool_calls"] = [{"name": "send_email", "arguments": "PRIVATE_SENTINEL"}]
    elif mutation == "status":
        payload["state"] = "mysterious"
    elif mutation == "empty":
        payload["review"] = None
    elif mutation == "unknown_source":
        payload["review"]["cited_passages"] = ["not.in.context"]
    elif mutation == "duplicate_source":
        payload["review"]["cited_passages"] *= 2
    elif mutation == "wrong_usage":
        payload["usage"]["output_tokens"] = True
    elif mutation == "false_verified":
        payload["review"]["semantic_support"] = "verified"
    elif mutation == "unknown_field":
        payload["review"]["credential"] = "PRIVATE_SENTINEL"
    elif mutation == "refusal_with_payload":
        payload["state"] = "refused"
    raw = b'not-json PRIVATE_SENTINEL' if mutation == "malformed" else json.dumps(payload).encode()
    trace = demo.ReadTrace({profiles[1].profile_id: raw})
    result = replay_inference(req, profiles, adm, trace, now=demo.NOW)
    assert result.outcome == "invalid_response" and result.proposal is None
    assert trace.reads == [profiles[1].profile_id]
    assert "PRIVATE_SENTINEL" not in result.model_dump_json()


@pytest.mark.parametrize("field,value", [("output_tokens", 513), ("elapsed_ms", 1001), ("cost_units", 11)])
def test_reported_budget_overrun_discards_proposal(setup, field, value):
    req, profiles, adm = setup
    wires = demo.fixture_wires(req)
    payload = json.loads(wires[profiles[1].profile_id])
    payload["usage"][field] = value
    wires[profiles[1].profile_id] = json.dumps(payload).encode()
    result = replay_inference(req, profiles, adm, wires, now=demo.NOW)
    assert result.outcome == "budget_exceeded" and result.proposal is None


def test_output_byte_budget(setup):
    req, profiles, _ = setup
    req = change(req, max_output_bytes=10)
    result = replay_inference(req, profiles, demo.fixture_admission(req, profiles),
                              demo.fixture_wires(req), now=demo.NOW)
    assert result.outcome == "budget_exceeded"


def test_semantic_correctness_not_inferred_from_contract_validity(setup):
    req, profiles, adm = setup
    wires = demo.fixture_wires(req)
    raw = json.loads(wires[profiles[1].profile_id])
    raw["review"]["summary"] = "Synthetic false assertion: software tests establish nurse competence."
    wires[profiles[1].profile_id] = json.dumps(raw).encode()
    result = replay_inference(req, profiles, adm, wires, now=demo.NOW)
    assert result.outcome == "proposal_ready"
    assert result.proposal.semantic_support == "not_verified"
    assert result.next_action == "human_review"


def test_no_network_client_needed(monkeypatch, setup):
    def prohibited(*args, **kwargs):
        pytest.fail("Offline replay attempted a socket")
    monkeypatch.setattr(socket, "socket", prohibited)
    req, profiles, adm = setup
    assert replay_inference(req, profiles, adm, demo.fixture_wires(req), now=demo.NOW).outcome == "proposal_ready"


def test_changed_grant_is_rechecked_not_a_reusable_old_plan(setup):
    req, profiles, adm = setup
    assert plan_inference(req, profiles, adm, now=demo.NOW).status == "eligible_fixture"
    trace = demo.ReadTrace(demo.fixture_wires(req))
    result = replay_inference(req, profiles, change(adm, disposition="deny"), trace, now=demo.NOW)
    assert result.outcome == "denied" and not trace.reads


def test_no_private_entry_field_or_whole_session_export(setup):
    req, _, _ = setup
    keys = req.model_dump().keys()
    assert not {"reflection", "soul", "memory", "history", "initial_interpretation", "approval"} & keys


def test_record_immutability_is_not_an_authority_claim(setup):
    req, _, _ = setup
    with pytest.raises(ValidationError):
        req.task = "changed"
    # Caller-crafted copies still get admission-binding checks; frozen is not a sandbox.
    assert change(req, task="different allowed text").task != req.task
