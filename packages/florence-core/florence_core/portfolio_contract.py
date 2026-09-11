"""Evaluate supplied save scenarios only. No filesystem, storage, callback or IO.

An internally matching fixture is NOT a saved portfolio or an ExecutionReceipt.
Actual authority, observation freshness, concurrency and durability need an executor
and a separately authorized store. Those components are deliberately absent here.
"""
from __future__ import annotations

import hashlib
import json

from .schemas.portfolio import SaveAssessment, SaveScenario, digest

ERROR = "Invalid portfolio test record; no storage or network operation performed."
MAX_INPUT_BYTES = 262144


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(ERROR)
        value[key] = item
    return value


def _constant(_):
    raise ValueError(ERROR)


def parse_scenario(raw: bytes) -> SaveScenario:
    try:
        if type(raw) is not bytes or not 0 < len(raw) <= MAX_INPUT_BYTES:
            raise ValueError(ERROR)
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_constant)
        json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        return SaveScenario.model_validate(value)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ValueError(ERROR) from None


def _content_matches(content, envelope):
    raw = content.encode("utf-8")
    return len(raw) <= 16000 and hashlib.sha256(raw).hexdigest() == envelope.artifact.content_sha256


def assess_save_fixture(scenario: SaveScenario) -> SaveAssessment:
    """Return evidence and guard results separately; NEVER return a live permit.

    Current expiry or later revocation does not erase historical byte evidence.
    A dispatch claim alone remains unknown, and cannot justify an automatic retry.
    """
    try:
        if type(scenario) is not SaveScenario:
            raise ValueError(ERROR)
        validated = SaveScenario.model_validate(scenario)
        s = parse_scenario(validated.model_dump_json().encode("utf-8"))
        entry_hash, intent_hash = digest(s.envelope), digest(s.intent)
        base = []
        if not _content_matches(s.content_utf8, s.envelope):
            base.append("content_hash_mismatch")
        if (s.intent.envelope_sha256 != entry_hash
                or s.intent.logical_key != s.envelope.logical_key()):
            base.append("intent_binding_mismatch")
        if s.intent.actor_ref != s.envelope.owner_ref:
            base.append("actor_owner_mismatch")
        if s.envelope.artifact.created_at > s.as_of:
            base.append("artifact_future_dated")

        def guards(at, audit):
            failures = list(base)
            p, a = s.policy, s.approval
            if p is None:
                failures.append("policy_missing")
            elif ((p.intent_sha256, p.policy_ref, p.policy_version) !=
                  (intent_hash, s.intent.policy_ref, s.intent.policy_version)):
                failures.append("policy_binding_mismatch")
            elif p.disposition != "allow_in_simulation" or not p.valid_from <= at < p.expires_at:
                failures.append("policy_denied_or_outside_window")
            if a is None:
                failures.append("approval_missing")
            elif (a.intent_sha256 != intent_hash or p is None or a.policy_sha256 != digest(p)
                    or a.approver_ref != s.envelope.owner_ref):
                failures.append("approval_binding_mismatch")
            elif (a.disposition != "confirm_in_simulation" or not a.approved_at <= at < a.expires_at
                  or a.approved_at < p.valid_from or a.approved_at >= p.expires_at):
                failures.append("approval_rejected_or_outside_window")
            if s.approval_revoked_at is not None and s.approval_revoked_at <= at:
                failures.append("approval_revoked")
            if not audit:
                failures.append("audit_unavailable")
            return failures

        current = guards(s.as_of, s.audit_available_now)
        historical = []
        state = "not_dispatched"
        next_step = "blocked_no_dispatch" if current else "fixture_ready_execution_disabled"
        a, r = s.attempt, s.readback
        if a is None and r is not None:
            current.append("readback_without_attempt")
            state, next_step = "unknown", "reconcile_without_retry"
        elif a is not None:
            historical = guards(a.dispatched_at, a.audit_recorded)
            if a.dispatched_at > s.as_of or a.dispatched_at < s.envelope.artifact.created_at:
                historical.append("attempt_chronology_invalid")
            if (a.intent_sha256 != intent_hash or s.policy is None or s.approval is None
                    or a.policy_sha256 != digest(s.policy) or a.approval_sha256 != digest(s.approval)):
                historical.append("attempt_chain_mismatch")
            next_step = "reconcile_without_retry"
            if a.logical_key != s.envelope.logical_key() or a.envelope_sha256 != entry_hash:
                state, next_step = "conflict", "inspect_conflict_no_overwrite"
            elif r is None or r.state == "unavailable":
                state = "in_flight" if a.reported_state == "in_flight" else "unknown"
            elif (r.operation_ref != a.operation_ref or not a.dispatched_at <= r.observed_at <= s.as_of):
                historical.append("readback_binding_or_time_invalid")
                state = "unknown"
            elif r.state == "absent":
                state = "absent_in_fixture"  # An absent read is not proof the write cannot later commit.
            elif digest(r.envelope) != entry_hash or not _content_matches(r.content_utf8, r.envelope):
                state, next_step = "readback_mismatch", "inspect_conflict_no_overwrite"
            else:
                state, next_step = "readback_matches_fixture", "inspect_matching_evidence_no_repeat"
                if a.reported_state == "reported_failure":
                    historical.append("failure_report_conflicts_with_readback")
        return SaveAssessment(envelope_sha256=entry_hash, current_guard_failures=tuple(current),
            historical_guard_failures=tuple(historical), evidence_state=state, next_step=next_step)
    except (ValueError, TypeError, UnicodeError, RecursionError, AttributeError):
        raise ValueError(ERROR) from None
