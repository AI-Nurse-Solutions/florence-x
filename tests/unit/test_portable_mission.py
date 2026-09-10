"""SS-01 acceptance and negative tests; fixtures are public synthetic metadata."""
from __future__ import annotations

import copy
import http.client
import importlib.util
import json
import threading
from pathlib import Path

import pytest
from florence_core.schemas.mission import (
    MissionInputError,
    WorkspaceBundle,
    inspect_profile,
    mission_digest,
    parse_workspace,
)
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
RAW = (ROOT / "examples/portable_learning/workspace.json").read_bytes()


def source():
    return json.loads(RAW)


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("profile", ["local", "hybrid", "hosted_test"])
def test_same_mission_across_all_profiles(profile):
    bundle = parse_workspace(RAW)
    before = bundle.mission.model_dump_json()
    result = inspect_profile(bundle, profile)
    assert result["mission_id"] == "mission.public-learning.0001"
    assert result["mission_sha256"] == mission_digest(bundle.mission)
    assert bundle.mission.model_dump_json() == before
    assert result["actual_processing"] == "none"
    assert result["authorization"] == "not_assessed_no_execution_interface"


def test_roundtrip():
    bundle = parse_workspace(RAW)
    assert parse_workspace(bundle.model_dump_json().encode()) == bundle
    assert len(mission_digest(bundle.mission)) == 64


@pytest.mark.parametrize("key,value", [
    ("schema_version", "9.9.9"), ("data_classification", "unknown"),
    ("data_classification", "internal"), ("data_classification", "phi_local"),
    ("purpose", "clinical_execution"), ("revision", True), ("revision", "1"),
    ("revision", 0), ("goal", "  "), ("mission_id", ""), ("owner_ref", ""),
    ("created_at", "2026-09-09T12:00:00"), ("stage", "completed"),
    ("record_state", "approved"), ("success_criteria", []), ("limitations", []),
    ("pillar_dependencies", ["knowledge", "knowledge", "contribution"]),
    ("tool", "terminal"), ("approval", "granted"), ("hermes_session_id", "opaque"),
])
def test_invalid_mission_metadata_is_rejected(key, value):
    data = source()
    data["mission"][key] = value
    with pytest.raises(MissionInputError):
        parse_workspace(json.dumps(data).encode())


@pytest.mark.parametrize("key,value", [
    ("profile", "unknown"), ("endpoint_ref", "https://unapproved.invalid/model"),
    ("endpoint_ref", "fixture.hosted-model"), ("mode", "live"),
    ("authority", "approved"), ("data_classification", "internal"),
    ("hermes", "connected"), ("network_enabled", True),
    ("persistence_enabled", True), ("inference_enabled", True),
    ("inference_enabled", "false"), ("inference_enabled", 0),
    ("command", "unapproved-command"),
])
def test_invalid_or_executable_manifest_rejected(key, value):
    data = source()
    data["manifests"][0][key] = value
    with pytest.raises(MissionInputError):
        parse_workspace(json.dumps(data).encode())


@pytest.mark.parametrize("field", ["interaction", "harness", "authoritative_storage", "inference"])
def test_unknown_placement_rejected(field):
    data = source()
    data["manifests"][0]["target_layout"][field] = "unknown"
    with pytest.raises(MissionInputError):
        parse_workspace(json.dumps(data).encode())


def test_hybrid_cannot_claim_local_inference():
    data = source()
    data["manifests"][1]["target_layout"]["inference"] = "device"
    with pytest.raises(MissionInputError):
        parse_workspace(json.dumps(data).encode())


@pytest.mark.parametrize("raw", [
    b"", b"null", b"[]", b"{}", b"\\xff", b"{", b"x" * 65537,
    b'{"schema_version":"0.1.0","schema_version":"0.1.0"}',
    b'{"value":NaN}', b'{"value":Infinity}', b'{"value":-Infinity}',
    b"[" * 1200 + b"]" * 1200,
])
def test_bounded_json_refusals_are_sanitized(raw):
    with pytest.raises(MissionInputError) as error:
        parse_workspace(raw)
    assert str(error.value) == "Invalid portable workspace; no operation performed."


@pytest.mark.parametrize("profile", ["unknown", "LOCAL", "", None, [], {}])
def test_unknown_profile_inspection_rejected(profile):
    with pytest.raises(MissionInputError):
        inspect_profile(parse_workspace(RAW), profile)


def test_changed_copied_model_is_revalidated():
    bundle = parse_workspace(RAW)
    invalid = bundle.mission.model_copy(update={"data_classification": "internal"})
    with pytest.raises(MissionInputError):
        mission_digest(invalid)
    copied = bundle.model_copy(update={"mission": invalid})
    with pytest.raises(MissionInputError):
        inspect_profile(copied, "local")


def test_copied_manifest_cannot_enable_execution():
    bundle = parse_workspace(RAW)
    bad = bundle.manifests[0].model_copy(update={"network_enabled": True})
    with pytest.raises(MissionInputError):
        inspect_profile(bundle.model_copy(update={"manifests": (bad, *bundle.manifests[1:])}), "local")


def test_duplicate_profile_rejected():
    data = source()
    data["manifests"][2] = copy.deepcopy(data["manifests"][0])
    with pytest.raises(MissionInputError):
        parse_workspace(json.dumps(data).encode())


def test_missing_source_classification_is_rejected():
    data = source()
    data["mission"]["sources"] = [{"source_id": "s1", "revision": "1", "content_sha256": "a"*64,
                                    "locator": "fixture", "origin": "synthetic_fixture", "applicability": "test"}]
    with pytest.raises(MissionInputError):
        parse_workspace(json.dumps(data).encode())


def test_inputs_not_echoed_in_public_errors():
    data = source()
    data["manifests"][0]["endpoint_ref"] = "PRIVATE_MARKER_NEVER_LOG"
    with pytest.raises(MissionInputError) as error:
        parse_workspace(json.dumps(data).encode())
    assert "PRIVATE_MARKER" not in str(error.value)


def test_models_reject_mutation_and_extra_fields():
    bundle = parse_workspace(RAW)
    with pytest.raises(ValidationError):
        bundle.mission.goal = "changed"
    with pytest.raises(ValidationError):
        WorkspaceBundle.model_validate({**source(), "execute": True})


def test_derived_html_matches_validated_fixture():
    script = load_script("build_learning_workspace")
    text = script.render()
    assert text == (ROOT / "apps/learning-workspace/index.html").read_text()
    assert "__DATA__" not in text and "__SCRIPT_HASH__" not in text
    assert "connect-src 'none'" in text
    assert "mission.public-learning.0001" in text


@pytest.fixture
def server():
    module = load_script("serve_learning_workspace")
    instance = module.make_server(0)
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield instance
    instance.shutdown()
    instance.server_close()
    thread.join(timeout=2)
    assert not thread.is_alive()


def request(server, method="GET", path="/", headers=None):
    client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    try:
        client.request(method, path, headers=headers or {})
        response = client.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        client.close()


def test_loopback_server_serves_only_bundled_preview(server):
    status, headers, body = request(server)
    assert status == 200
    assert body == (ROOT / "apps/learning-workspace/index.html").read_bytes()
    assert headers["Cache-Control"] == "no-store"
    assert headers["X-Frame-Options"] == "DENY"
    assert server.server_address[0] == "127.0.0.1"


@pytest.mark.parametrize("path", ["/../../etc/passwd", "/%2e%2e/config", "/api/missions", "/?token=example"])
def test_other_paths_refused(server, path):
    assert request(server, path=path)[0] == 404


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_write_methods_refused(server, method):
    assert request(server, method=method)[0] == 405


@pytest.mark.parametrize("headers", [{"Host": "untrusted.invalid"}, {"Origin": "https://untrusted.invalid"}])
def test_untrusted_host_or_origin_refused(server, headers):
    assert request(server, headers=headers)[0] == 403


def test_head_has_no_body(server):
    status, headers, body = request(server, method="HEAD")
    assert status == 200 and body == b"" and int(headers["Content-Length"]) > 1000
