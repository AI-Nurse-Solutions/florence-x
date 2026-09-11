"""Pure SS-06A assertions; supplied evidence is never an actual persistence test."""
from __future__ import annotations

import builtins
import copy
import importlib.util
import json
import socket
from datetime import timedelta
from pathlib import Path

import pytest

from florence_core.portfolio_contract import ERROR, assess_save_fixture, parse_scenario
from florence_core.schemas.portfolio import PortfolioEnvelope, SaveScenario, digest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("portfolio_examples", ROOT / "scripts/portfolio_contract_demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


@pytest.fixture
def base():
    return demo.example()


def test_good_fixture_has_no_write_or_success_receipt(base):
    out = assess_save_fixture(base)
    assert out.current_guard_failures == () and out.evidence_state == "not_dispatched"
    assert out.next_step == "fixture_ready_execution_disabled"
    assert out.storage_operations == 0 and out.successful_receipt_issued is False
    assert out.operational_saving == "disabled" and out.real_persistence == "not_observed"


def test_exact_catalog_metadata_is_retained(base):
    a = base.envelope.artifact
    assert base.envelope.owner_ref == a.owner_ref
    assert a.sources and a.ai_assistance.used and a.ai_assistance.method
    assert a.publication_state == "draft" and base.envelope.audience == "owner_only"
    assert base.envelope.contribution_state == "not_submitted"
    assert base.envelope.competence == "not_assessed"
    assert base.envelope.mission_sha256 == "e3cf03292e21a46b5a3f6297b29da8354e087473995084abe8b9150106e50072"


@pytest.mark.parametrize("field,value", [
    ("purpose", "Another purpose"), ("workspace_ref", "workspace.another"),
    ("destination_ref", "portfolio.another"), ("mission_id", "mission.another"),
    ("mission_sha256", "a" * 64), ("learning_decision_sha256", "b" * 64),
])
def test_envelope_changes_invalidate_intent(base, field, value):
    changed = demo.replace(base, envelope=demo.replace(base.envelope, **{field: value}))
    out = assess_save_fixture(changed)
    assert "intent_binding_mismatch" in out.current_guard_failures
    assert out.next_step == "blocked_no_dispatch"


@pytest.mark.parametrize("field,value", [("version", "0.2.0"), ("title", "Changed title"),
                                        ("content_sha256", "a" * 64)])
def test_artifact_change_cannot_reuse_bound_intent(base, field, value):
    artifact = demo.replace(base.envelope.artifact, **{field: value})
    changed = demo.replace(base, envelope=demo.replace(base.envelope, artifact=artifact))
    assert "intent_binding_mismatch" in assess_save_fixture(changed).current_guard_failures


def test_changed_source_revision_invalidates_old_chain(base):
    a = base.envelope.artifact
    sources = (demo.replace(a.sources[0], revision="Changed source"), *a.sources[1:])
    changed = demo.replace(base, envelope=demo.replace(base.envelope, artifact=demo.replace(a, sources=sources)))
    assert "intent_binding_mismatch" in assess_save_fixture(changed).current_guard_failures


@pytest.mark.parametrize("field", ["policy", "approval"])
def test_missing_chain_record_blocks(base, field):
    out = assess_save_fixture(demo.replace(base, **{field: None}))
    assert field + "_missing" in out.current_guard_failures
    assert out.successful_receipt_issued is False


def test_learning_choice_cannot_replace_save_approval(base):
    data = base.model_dump(mode="json")
    data["approval"] = {"outcome": "accept", "reason": "Useful", "alternative": "Wait", "consequence": "Learn"}
    with pytest.raises(ValueError, match=ERROR):
        parse_scenario(json.dumps(data).encode())


@pytest.mark.parametrize("field,value", [("actor_ref", "actor.other"),
    ("capability_version", "0.2.0"), ("policy_ref", "policy.other"), ("policy_version", "0.2.0")])
def test_actor_capability_and_policy_versions_are_bound(base, field, value):
    changed = demo.replace(base, intent=demo.replace(base.intent, **{field: value}))
    out = assess_save_fixture(changed)
    assert out.current_guard_failures and out.next_step == "blocked_no_dispatch"


@pytest.mark.parametrize("field,value", [("approver_ref", "actor.other"), ("disposition", "reject"),
    ("intent_sha256", "a" * 64), ("policy_sha256", "b" * 64)])
def test_approval_mismatch_or_rejection_stops(base, field, value):
    changed = demo.replace(base, approval=demo.replace(base.approval, **{field: value}))
    assert assess_save_fixture(changed).current_guard_failures


@pytest.mark.parametrize("delta", [-100, 20, 200])
def test_approval_window_is_half_open(base, delta):
    changed = demo.replace(base, as_of=demo.NOW + timedelta(minutes=delta))
    assert "approval_rejected_or_outside_window" in assess_save_fixture(changed).current_guard_failures


def test_revocation_at_dispatch_is_historical_failure(base):
    s = demo.matched(base)
    out = assess_save_fixture(demo.replace(s, approval_revoked_at=s.attempt.dispatched_at))
    assert "approval_revoked" in out.historical_guard_failures
    assert out.evidence_state == "readback_matches_fixture"  # Observation cannot be erased by permission failure.
    assert out.authority == "no_execution_permission"


def test_later_expiry_and_revocation_preserve_historical_observation(base):
    s = demo.matched(base)
    out = assess_save_fixture(demo.replace(s, as_of=demo.NOW + timedelta(hours=2),
        approval_revoked_at=demo.NOW - timedelta(minutes=1)))
    assert out.current_guard_failures and out.historical_guard_failures == ()
    assert out.evidence_state == "readback_matches_fixture" and not out.successful_receipt_issued


def test_unavailable_audit_before_and_after_dispatch_are_distinct(base):
    assert "audit_unavailable" in assess_save_fixture(demo.replace(base, audit_available_now=False)).current_guard_failures
    s = demo.matched(base)
    out = assess_save_fixture(demo.replace(s, attempt=demo.replace(s.attempt, audit_recorded=False)))
    assert "audit_unavailable" in out.historical_guard_failures
    assert out.evidence_state == "readback_matches_fixture" and not out.successful_receipt_issued


@pytest.mark.parametrize("state,expected", [("reported_success", "unknown"), ("reported_failure", "unknown"),
    ("outcome_unknown", "unknown"), ("in_flight", "in_flight")])
def test_attempt_without_readback_never_reports_saved_or_retries(base, state, expected):
    out = assess_save_fixture(demo.attempted(base, state))
    assert out.evidence_state == expected and out.next_step == "reconcile_without_retry"
    assert out.successful_receipt_issued is False


def test_matching_full_readback_is_explicit_fixture_only(base):
    out = assess_save_fixture(demo.matched(base))
    assert out.evidence_state == "readback_matches_fixture"
    assert out.next_step == "inspect_matching_evidence_no_repeat"
    assert out.real_persistence == "not_observed" and out.storage_operations == 0


def test_duplicate_request_is_pure_and_does_not_mutate_or_resubmit(base):
    s = demo.matched(base)
    before = s.model_dump_json()
    first = assess_save_fixture(s)
    for _ in range(3):
        assert assess_save_fixture(s) == first
    assert s.model_dump_json() == before and first.storage_operations == 0


def test_conflicting_target_content_is_not_overwritten(base):
    s = demo.matched(base)
    new_entry = demo.replace(s.envelope, purpose="A different intent at the same key")
    assert new_entry.logical_key() == s.envelope.logical_key()
    out = assess_save_fixture(demo.replace(s, envelope=new_entry))
    assert out.evidence_state == "conflict" and out.next_step == "inspect_conflict_no_overwrite"


@pytest.mark.parametrize("field,value", [("operation_ref", "operation.other"),
    ("observed_at", demo.NOW - timedelta(hours=3)), ("observed_at", demo.NOW + timedelta(hours=1))])
def test_unbound_or_badly_timed_readback_is_unknown(base, field, value):
    s = demo.matched(base)
    out = assess_save_fixture(demo.replace(s, readback=demo.replace(s.readback, **{field: value})))
    assert out.evidence_state == "unknown" and "readback_binding_or_time_invalid" in out.historical_guard_failures


@pytest.mark.parametrize("field,value", [("intent_sha256", "a" * 64), ("policy_sha256", "b" * 64),
                                        ("approval_sha256", "c" * 64)])
def test_forged_attempt_cannot_claim_clean_history(base, field, value):
    s = demo.matched(base)
    out = assess_save_fixture(demo.replace(s, attempt=demo.replace(s.attempt, **{field: value})))
    assert "attempt_chain_mismatch" in out.historical_guard_failures
    assert out.successful_receipt_issued is False


def test_readback_requires_actual_content_comparison_not_echoed_hash(base):
    s = demo.matched(base)
    out = assess_save_fixture(demo.replace(s, readback=demo.replace(s.readback, content_utf8="PRIVATE_SENTINEL")))
    assert out.evidence_state == "readback_mismatch"
    assert "PRIVATE_SENTINEL" not in out.model_dump_json()


def test_readback_checks_metadata_not_only_content(base):
    s = demo.matched(base)
    e = demo.replace(s.envelope, destination_ref="wrong.destination")
    out = assess_save_fixture(demo.replace(s, readback=demo.replace(s.readback, envelope=e)))
    assert out.evidence_state == "readback_mismatch"


@pytest.mark.parametrize("state,expected", [("absent", "absent_in_fixture"), ("unavailable", "unknown")])
def test_missing_readback_requires_reconciliation_not_retry(base, state, expected):
    s = demo.matched(base)
    r = demo.replace(s.readback, state=state, envelope=None, content_utf8=None)
    out = assess_save_fixture(demo.replace(s, readback=r))
    assert out.evidence_state == expected and out.next_step == "reconcile_without_retry"


def test_readback_without_attempt_is_not_a_receipt(base):
    s = demo.matched(base)
    out = assess_save_fixture(demo.replace(s, attempt=None))
    assert "readback_without_attempt" in out.current_guard_failures
    assert not out.successful_receipt_issued


def test_failure_report_and_matching_bytes_remain_contestable(base):
    s = demo.matched(base)
    out = assess_save_fixture(demo.replace(s, attempt=demo.replace(s.attempt, reported_state="reported_failure")))
    assert "failure_report_conflicts_with_readback" in out.historical_guard_failures


@pytest.mark.parametrize("raw", [b'', b'{', b'null', b'[]', b'{"x":1,"x":2}', b'{"x":NaN}',
    b'\xff', b'{}\n{}', b'x' * 262145, bytearray(b'{}'), b'\xff\xfe{\0}\0', b'{"x":"\\ud800"}'])
def test_parser_denies_invalid_inputs_without_echo(raw):
    with pytest.raises(ValueError, match=ERROR) as exc:
        parse_scenario(raw)
    assert str(exc.value) == ERROR


@pytest.mark.parametrize("field,value", [("audience", "community"), ("competence", "certified"),
    ("contribution_state", "published"), ("destination_ref", "../../private"), ("owner_ref", "other.owner")])
def test_private_envelope_cannot_silently_promote_or_use_path(base, field, value):
    data = base.envelope.model_dump()
    data[field] = value
    with pytest.raises(ValueError):
        PortfolioEnvelope.model_validate(data)


@pytest.mark.parametrize("field,value", [("authority", "authorized"), ("origin", "live_store"),
    ("audit_available_now", "true"), ("audit_available_now", 1), ("as_of", "2026-09-10T12:00:00")])
def test_fixture_cannot_claim_live_identity_or_coerce_controls(base, field, value):
    raw = base.model_dump(mode="json")
    raw[field] = value
    with pytest.raises(ValueError, match=ERROR):
        parse_scenario(json.dumps(raw).encode())


@pytest.mark.parametrize("value", [True, 0, "false", None])
def test_overwrite_disabled_is_not_coerced(base, value):
    raw = base.model_dump(mode="json")
    raw["intent"]["overwrite"] = value
    with pytest.raises(ValueError, match=ERROR):
        parse_scenario(json.dumps(raw).encode())


def test_constructed_invalid_instance_is_revalidated(base):
    bad = base.model_copy(update={"audit_available_now": "true"})
    with pytest.raises(ValueError, match=ERROR):
        assess_save_fixture(bad)


def test_unknown_fields_are_not_ignored(base):
    raw = base.model_dump(mode="json")
    raw["private_reflection"] = "PRIVATE_SENTINEL"
    with pytest.raises(ValueError, match=ERROR) as exc:
        parse_scenario(json.dumps(raw).encode())
    assert "PRIVATE_SENTINEL" not in str(exc.value)


def test_assessor_has_no_file_or_socket_access(base, monkeypatch):
    s = demo.matched(base)
    def denied(*args, **kwargs):
        pytest.fail("Pure assessor attempted external IO")
    monkeypatch.setattr(builtins, "open", denied)
    monkeypatch.setattr(Path, "open", denied)
    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    out = assess_save_fixture(s)
    assert out.storage_operations == 0 and not out.successful_receipt_issued


def test_each_report_scenario_remains_explicitly_nonoperational():
    result = demo.evaluate()
    assert len(result["cases"]) == 14
    assert all(row["result"]["authority"] == "no_execution_permission" for row in result["cases"])
    assert all(row["result"]["real_persistence"] == "not_observed" for row in result["cases"])


def test_input_digest_and_source_record_not_mutated(base):
    before = copy.deepcopy(base.model_dump(mode="json"))
    assess_save_fixture(base)
    assert before == base.model_dump(mode="json")
    assert parse_scenario(base.model_dump_json().encode()) == base
    assert digest(base.envelope) == base.intent.envelope_sha256
