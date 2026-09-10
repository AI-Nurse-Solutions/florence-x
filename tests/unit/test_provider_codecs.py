"""SS-05B: documented format subsets tested with authored fixtures, no providers."""
from __future__ import annotations

import copy
import importlib.util
import json
import socket
from pathlib import Path

import pytest
from florence_core.schemas.inference import InferenceRequest, fingerprint
from florence_core.schemas.provider_codec import ProviderCodecSpec
from florence_model_router.provider_codecs import ERROR, decode_fixture, prepare_request, proposal_schema

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("codec_demo_inputs", ROOT / "scripts/model_contract_demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
PROTOCOLS = ("ollama_chat_v1", "openai_chat_completions_v1")


def change(record, **updates):
    return type(record).model_validate({**record.model_dump(), **updates})


@pytest.fixture(params=PROTOCOLS)
def case(request):
    req = demo.demo_inputs()[0][0]
    fixtures = json.loads((ROOT / "examples/provider_codecs/responses.json").read_text())
    protocol = request.param
    cfg = ProviderCodecSpec(profile_id="codec.test", protocol=protocol,
        request_model=fixtures["model"], expected_response_model=fixtures["model"])
    wire = fixtures[protocol]
    msg = wire["message"] if protocol == "ollama_chat_v1" else wire["choices"][0]["message"]
    msg["content"] = json.dumps(fixtures["proposal"])
    return req, cfg, wire, msg


def decode(case, wire=None, req=None, **kw):
    original, cfg, base, _ = case
    current = req or original
    return decode_fixture(current, prepare_request(current, cfg), json.dumps(wire or base).encode(), **kw)


def test_request_mapping_preserves_context_without_provider_owning_record(case):
    req, cfg, _, _ = case
    before = req.model_dump_json()
    prepared = prepare_request(req, cfg)
    body = json.loads(prepared.body_json)
    assert prepared.request_sha256 == fingerprint(req)
    assert prepared.mission_sha256 == req.mission_sha256
    assert prepared.authority == "no_execution_permission" and prepared.transmission == "not_implemented"
    assert body["stream"] is False and body["model"] == cfg.request_model
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    actual = json.loads(body["messages"][1]["content"])
    assert actual == {"task": req.task, "passages": [{"passage_id": x.passage_id,
        "source_id": x.source.source_id, "revision": x.source.revision,
        "excerpt_sha256": x.source.content_sha256, "applicability": x.source.applicability,
        "excerpt": x.excerpt} for x in req.context]}
    for private_field in ("mission_id", "owner_ref", "workspace_ref", "reflection", "api_key", "tools"):
        assert private_field not in body and private_field not in actual
    assert req.model_dump_json() == before
    assert prepare_request(req, cfg) == prepared


def test_provider_specific_fields_are_not_generic_api_guesses(case):
    req, cfg, _, _ = case
    prepared = prepare_request(req, cfg)
    body = json.loads(prepared.body_json)
    if cfg.protocol == "ollama_chat_v1":
        assert prepared.relative_path == "/api/chat"
        assert set(body) == {"model", "messages", "stream", "format", "options"}
        assert body["format"] == proposal_schema()
        assert body["options"] == {"num_predict": req.max_output_tokens}
    else:
        assert prepared.relative_path == "/v1/chat/completions"
        assert set(body) == {"model", "messages", "stream", "store", "n", "max_completion_tokens", "response_format"}
        assert body["store"] is False and body["n"] == 1
        assert body["max_completion_tokens"] == req.max_output_tokens
        assert body["response_format"] == {"type": "json_schema", "json_schema": {
            "name": "resource_review_v1", "strict": True, "schema": proposal_schema()}}


def test_complete_response_keeps_review_and_source_limits(case):
    req, _, _, _ = case
    out = decode(case)
    assert out.outcome == "proposal_ready"
    assert out.proposal.semantic_support == "not_verified"
    assert out.proposal.review_status == "not_independently_reviewed"
    assert out.next_action == "human_review" and out.transport_calls == 0
    assert out.request_sha256 == fingerprint(req)
    assert out.token_counts.output_tokens == 70
    assert out.token_counts.basis == "authored_provider_format_fixture"


@pytest.mark.parametrize("feature", ["tool_proposals", "image_input", "streaming"])
def test_unsupported_input_features_do_not_get_downgraded(case, feature):
    req, cfg, _, _ = case
    with pytest.raises(ValueError, match=ERROR):
        prepare_request(change(req, required_features=("structured_output", feature)), cfg)


def test_explicit_profile_is_not_substituted(case):
    req, cfg, _, _ = case
    with pytest.raises(ValueError, match=ERROR):
        prepare_request(change(req, requested_profile="another.profile"), cfg)


@pytest.mark.parametrize("field,value", [("task", "Changed task"), ("mission_id", "other.mission"),
                                         ("max_output_tokens", 256)])
def test_old_preparation_cannot_be_rebound(case, field, value):
    req, cfg, wire, _ = case
    with pytest.raises(ValueError, match=ERROR):
        decode_fixture(change(req, **{field: value}), prepare_request(req, cfg), json.dumps(wire).encode())


def test_modified_body_is_rejected_even_with_a_hash(case):
    req, cfg, wire, _ = case
    prep = prepare_request(req, cfg)
    with pytest.raises(ValueError, match=ERROR):
        decode_fixture(req, change(prep, body_json='{"tools":["shell"]}'), json.dumps(wire).encode())


@pytest.mark.parametrize("raw", [b'', b'{', b'null', b'[]', b'{"x":1,"x":2}', b'{"x":NaN}',
    b'\xff', b'{}\n{}', b'x' * 65537, bytearray(b'{}'), b'\xff\xfe{\0}\0'])
def test_invalid_wire_is_stopped_without_raw_error_content(case, raw):
    req, cfg, _, _ = case
    out = decode_fixture(req, prepare_request(req, cfg), raw)
    assert out.outcome == "invalid_response" and out.next_action == "stop_no_fallback"
    assert out.proposal is None and out.transport_calls == 0


@pytest.mark.parametrize("status", [301, 400, 401, 403, 429, 500])
def test_http_failure_never_echoes_body_or_retries(case, status):
    req, cfg, _, _ = case
    out = decode_fixture(req, prepare_request(req, cfg), b'PRIVATE_SENTINEL', status_code=status)
    assert out.outcome == "provider_error"
    assert "PRIVATE_SENTINEL" not in out.model_dump_json()
    assert out.transport_calls == 0 and out.next_action == "stop_no_fallback"


def test_unknown_model_is_not_silently_accepted(case):
    _, _, wire, _ = case
    wire["model"] = "different-model"
    assert decode(case).outcome == "invalid_response"


def test_unknown_top_level_field_fails_closed(case):
    _, _, wire, _ = case
    wire["unassessed_vendor_extension"] = {"content": "PRIVATE_SENTINEL"}
    out = decode(case)
    assert out.outcome == "invalid_response" and "PRIVATE_SENTINEL" not in out.model_dump_json()


def test_tool_calls_are_never_normalized_into_a_draft(case):
    _, _, _, message = case
    message["tool_calls"] = [{"function": {"name": "shell", "arguments": {"command": "fixture"}}}]
    assert decode(case).outcome == "unsupported_response"


def test_partial_json_never_gets_a_success_label(case):
    _, cfg, wire, msg = case
    msg["content"] = '{"summary":"partial'
    if cfg.protocol == "ollama_chat_v1":
        wire["done"] = False
    else:
        wire["choices"][0]["finish_reason"] = "length"
    assert decode(case).outcome == "incomplete"


def test_unknown_finish_reason_stops(case):
    _, cfg, wire, _ = case
    if cfg.protocol == "ollama_chat_v1":
        wire["done_reason"] = "load"
    else:
        wire["choices"][0]["finish_reason"] = "new_unknown_status"
    assert decode(case).outcome == "unsupported_response"


def test_missing_usage_is_unknown_not_free_inference(case):
    _, cfg, wire, _ = case
    if cfg.protocol == "ollama_chat_v1":
        wire.pop("eval_count")
        wire.pop("prompt_eval_count")
    else:
        wire.pop("usage")
    out = decode(case)
    assert out.outcome == "proposal_ready"
    assert out.token_counts is None or out.token_counts.output_tokens is None
    assert "cost" not in type(out).model_fields


@pytest.mark.parametrize("value", [True, -1, "70", 1000001])
def test_invalid_token_counts_are_not_coerced(case, value):
    _, cfg, wire, _ = case
    if cfg.protocol == "ollama_chat_v1":
        wire["eval_count"] = value
    else:
        wire["usage"]["completion_tokens"] = value
    assert decode(case).outcome == "invalid_response"


def test_usage_limit_is_a_postdecode_check_not_live_budget_enforcement(case):
    req, _, _, _ = case
    assert decode(case, req=change(req, max_output_tokens=60)).outcome == "budget_exceeded"
    assert decode(case, req=change(req, max_output_bytes=20)).outcome == "budget_exceeded"


@pytest.mark.parametrize("changes", [{"cited_passages": ["unknown"]},
    {"cited_passages": ["nist-scope", "nist-scope"]}, {"semantic_support": "verified"},
    {"review_status": "approved"}, {"tools": ["shell"]}])
def test_invalid_proposal_never_inherits_authority(case, changes):
    _, _, _, msg = case
    proposal = json.loads(msg["content"])
    proposal.update(changes)
    msg["content"] = json.dumps(proposal)
    assert decode(case).outcome == "invalid_response"


def test_false_well_formed_content_remains_unverified(case):
    _, _, _, msg = case
    proposal = json.loads(msg["content"])
    proposal["summary"] = "Deliberately false teaching assertion: citations guarantee effectiveness."
    msg["content"] = json.dumps(proposal)
    out = decode(case)
    assert out.outcome == "proposal_ready" and out.proposal.semantic_support == "not_verified"
    assert out.next_action == "human_review"


def test_no_socket_call_on_encoding_or_any_decode_path(case, monkeypatch):
    def refused(*args, **kwargs):
        pytest.fail("Codec attempted network access")
    monkeypatch.setattr(socket, "socket", refused)
    monkeypatch.setattr(socket, "create_connection", refused)
    assert decode(case).transport_calls == 0
    assert decode(case, status_code=500).outcome == "provider_error"


def test_openai_refusal_is_not_parsed_as_proposal():
    req = demo.demo_inputs()[0][0]
    cfg = ProviderCodecSpec(profile_id="codec.test", protocol=PROTOCOLS[1],
        request_model="fixture", expected_response_model="fixture")
    wire = {"id": "refusal-fixture", "object": "chat.completion", "created": 1, "model": "fixture",
        "choices": [{"index": 0, "finish_reason": "stop", "message": {
            "role": "assistant", "content": None, "refusal": "PRIVATE_SENTINEL"}}]}
    out = decode_fixture(req, prepare_request(req, cfg), json.dumps(wire).encode())
    assert out.outcome == "refused" and "PRIVATE_SENTINEL" not in out.model_dump_json()


def test_ollama_thinking_is_discarded_and_declared():
    req = demo.demo_inputs()[0][0]
    cfg = ProviderCodecSpec(profile_id="codec.test", protocol=PROTOCOLS[0],
        request_model="fixture", expected_response_model="fixture")
    proposal = {"summary": "Test", "limitations": ["Fixture"], "cited_passages": ["nist-scope"],
        "semantic_support": "not_verified", "review_status": "not_independently_reviewed"}
    wire = {"model": "fixture", "created_at": "2026-09-10T00:00:00Z", "done": True, "done_reason": "stop",
        "message": {"role": "assistant", "content": json.dumps(proposal), "thinking": "PRIVATE_SENTINEL"}}
    out = decode_fixture(req, prepare_request(req, cfg), json.dumps(wire).encode())
    assert out.outcome == "proposal_ready" and "message.thinking" in out.discarded_fields
    assert "PRIVATE_SENTINEL" not in out.model_dump_json()


def test_documented_schema_has_all_required_keys_and_no_extra_properties():
    s = proposal_schema()
    assert set(s["required"]) == set(s["properties"])
    assert s["additionalProperties"] is False


def test_fixture_catalog_is_not_mutated(case):
    original = copy.deepcopy(case[2])
    decode(case)
    assert case[2] == original
