"""SS-03 state and binding tests; no inference about professional competence."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from florence_core.schemas.deliberation import (
    DeliberationInputError,
    DeliberationPack,
    DeliberationSession,
    digest_record,
    parse_pack,
    start_session,
    transition,
    validate_session,
)
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
RAW = (ROOT / "examples/learning_deliberation/practice-pack.json").read_bytes()
PACK = parse_pack(RAW)
CASE = PACK.cases[0].case_id


def fresh():
    return start_session(PACK, CASE)


def apply(session, action, payload=None):
    return transition(session, PACK, action, payload)


def committed():
    return apply(fresh(), "commit", {"text": "Inspect scope and missing outcomes.", "uncertain": False})


def compared():
    return apply(committed(), "reveal")


def choice(outcome="reject"):
    return {"outcome": outcome, "reason": "Text integrity is not outcome evidence.",
            "alternative": "Pilot a smaller learning activity.",
            "consequence": "More review effort, with less unsupported certainty.",
            "replacement": "A draft to evaluate, not a validated intervention." if outcome == "revise" else None}


def encode(data):
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def test_pack_binding_matches_existing_mission_and_fixed_evidence():
    import hashlib

    from florence_core.schemas.mission import mission_digest, parse_workspace

    mission = parse_workspace((ROOT / "examples/portable_learning/workspace.json").read_bytes()).mission
    assert PACK.mission_sha256 == mission_digest(mission)
    assert PACK.mission_id == mission.mission_id
    assert PACK.evidence_raw_sha256 == hashlib.sha256(
        (ROOT / "examples/learning_evidence/public-pack.json").read_bytes()).hexdigest()
    assert {c.kind for c in PACK.cases} == {"omission", "competing_findings", "unsupported_certainty"}


@pytest.mark.parametrize("outcome", ["accept", "revise", "reject", "withhold"])
def test_all_choices_follow_same_valid_flow_and_remain_non_authoritative(outcome):
    first = committed()
    assert first.rounds[0].revealed is False
    second = apply(first, "reveal")
    third = apply(second, "choose", choice(outcome))
    final = apply(third, "reflect", {"text": "I need better evidence, not more persuasive wording."})
    assert first.rounds[0].decision is None  # Never mutate previous snapshot.
    assert final.rounds[0].decision.outcome == outcome
    assert final.rounds[0].reflection
    assert final.authority == "no_execution_permission"
    assert final.persistence == "memory_only"
    assert validate_session(final.model_dump_json().encode(), PACK) == final


@pytest.mark.parametrize("initial", [{"text": None, "uncertain": True},
                                     {"text": "Not enough information.", "uncertain": True}])
def test_uncertainty_is_a_valid_initial_response(initial):
    state = apply(fresh(), "commit", initial)
    assert state.rounds[0].initial.uncertain
    assert apply(state, "reveal").rounds[0].revealed


@pytest.mark.parametrize("action,payload", [("reveal", {}), ("choose", choice()),
    ("reflect", {"text": "No prior decision"}), ("execute", {}),
    ("commit", {"text": None, "uncertain": False}),
    ("commit", {"text": "   ", "uncertain": False}),
    ("commit", {"text": "x", "uncertain": "false"}),
    ("commit", {"text": "x", "uncertain": 0}),
    ("commit", {"text": "x", "uncertain": False, "approval": True})])
def test_invalid_order_and_initial_inputs_do_not_change_state(action, payload):
    state = fresh()
    before = state.model_dump_json()
    with pytest.raises(DeliberationInputError):
        apply(state, action, payload)
    assert state.model_dump_json() == before


@pytest.mark.parametrize("action,payload", [("commit", {"text": "overwrite", "uncertain": False}),
    ("reveal", {"extra": True})])
def test_committed_interpretation_is_not_rewritten(action, payload):
    with pytest.raises(DeliberationInputError):
        apply(committed(), action, payload)


@pytest.mark.parametrize("key,value", [("outcome", "approve"), ("reason", " "),
    ("alternative", None), ("consequence", ""), ("reason", "x"*2001),
    ("authorization", "allowed"), ("replacement", "Only revise may supply replacement")])
def test_invalid_choices_fail(key, value):
    payload = choice()
    payload[key] = value
    with pytest.raises(DeliberationInputError):
        apply(compared(), "choose", payload)


def test_revision_requires_actual_replacement():
    payload = choice("revise")
    payload["replacement"] = None
    with pytest.raises(DeliberationInputError):
        apply(compared(), "choose", payload)


def test_cannot_reveal_choose_or_reflect_twice():
    state = compared()
    with pytest.raises(DeliberationInputError):
        apply(state, "reveal")
    state = apply(state, "choose", choice())
    with pytest.raises(DeliberationInputError):
        apply(state, "choose", choice("accept"))
    state = apply(state, "reflect", {"text": "a reflection"})
    with pytest.raises(DeliberationInputError):
        apply(state, "reflect", {"text": "overwrite"})


@pytest.mark.parametrize("reason", ["context_changed", "evidence_view_changed"])
def test_stale_round_retains_decision_but_requires_new_initial_and_reveal(reason):
    state = apply(compared(), "choose", choice())
    original = state.rounds[0].decision.model_dump_json()
    stale = apply(state, "invalidate", {"reason": reason})
    with pytest.raises(DeliberationInputError):
        apply(stale, "reflect", {"text": "attempt to extend stale decision"})
    next_state = apply(stale, "restart", {"case_id": PACK.cases[1].case_id})
    assert next_state.rounds[0].decision.model_dump_json() == original
    assert next_state.rounds[0].closed_reason == reason
    assert next_state.rounds[1].initial is None and not next_state.rounds[1].revealed
    assert next_state.rounds[1].context_sha256 != next_state.rounds[0].context_sha256
    assert next_state.pack_sha256 == state.pack_sha256


@pytest.mark.parametrize("stage", [fresh, committed, compared])
def test_pause_blocks_transitions_but_allows_invalidation(stage):
    paused = apply(stage(), "pause")
    for action, payload in [("commit", {"text": "x", "uncertain": False}),
                             ("reveal", {}), ("choose", choice()), ("restart", {"case_id": CASE})]:
        with pytest.raises(DeliberationInputError):
            apply(paused, action, payload)
    stale = apply(paused, "invalidate", {"reason": "context_changed"})
    resumed = apply(stale, "pause")
    assert not resumed.paused and resumed.rounds[-1].closed_reason == "context_changed"


def test_pause_preserves_history_and_resume_allows_valid_next_step():
    state = committed()
    resumed = apply(apply(state, "pause"), "pause")
    assert resumed == state
    assert apply(resumed, "reveal").rounds[0].revealed


def test_round_budget_is_not_reset_by_pause_or_invalidation():
    state = fresh()
    for _ in range(11):
        state = apply(state, "restart", {"case_id": CASE})
    assert len(state.rounds) == 12
    with pytest.raises(DeliberationInputError):
        apply(apply(apply(state, "pause"), "pause"), "restart", {"case_id": CASE})


@pytest.mark.parametrize("case_id", ["unknown", "", "CASE.SCOPE", None, [], {}])
def test_unknown_case_rejected(case_id):
    with pytest.raises(DeliberationInputError):
        start_session(PACK, case_id)


@pytest.mark.parametrize("raw", [b"", b"null", b"[]", b"{}", b"x"*65537, b"\xff",
    b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1,"x":1}', b'['*1500+b']'*1500])
def test_bad_pack_json_sanitized(raw):
    with pytest.raises(DeliberationInputError) as e:
        parse_pack(raw)
    assert str(e.value) == "Invalid or out-of-order practice request; nothing changed."


@pytest.mark.parametrize("key,value", [("mission_id", "wrong.mission"),
    ("mission_sha256", "0"*64), ("pack_sha256", "0"*64), ("authority", "allowed"),
    ("persistence", "saved"), ("actor_status", "verified_nurse"), ("paused", "false"),
    ("execute", True)])
def test_session_does_not_silently_accept_unknown_authority_or_binding(key, value):
    data = fresh().model_dump(mode="json")
    data[key] = value
    with pytest.raises(DeliberationInputError):
        validate_session(encode(data), PACK)


def test_snapshot_with_changed_proposal_is_rejected_even_with_new_hash():
    data = compared().model_dump(mode="json")
    data["rounds"][0]["case"]["proposal"] = "Different proposal"
    with pytest.raises(DeliberationInputError):
        validate_session(encode(data), PACK)
    from florence_core.schemas.deliberation import PracticeCase

    data["rounds"][0]["context_sha256"] = digest_record(PracticeCase.model_validate(data["rounds"][0]["case"]))
    with pytest.raises(DeliberationInputError):
        validate_session(encode(data), PACK)


def test_pack_duplicate_case_or_kind_or_passage_is_rejected():
    for field in ["case_id", "kind"]:
        data = json.loads(RAW)
        data["cases"][1][field] = data["cases"][0][field]
        with pytest.raises(DeliberationInputError):
            parse_pack(encode(data))
    data = json.loads(RAW)
    data["cases"][0]["passage_ids"] *= 2
    with pytest.raises(DeliberationInputError):
        parse_pack(encode(data))


def test_copy_update_is_revalidated_and_errors_do_not_echo_input():
    copied = fresh().model_copy(update={"scope": "PRIVATE_DO_NOT_ECHO"})
    with pytest.raises(DeliberationInputError) as e:
        apply(copied, "pause")
    assert "PRIVATE_DO_NOT_ECHO" not in str(e.value)
    broken = PACK.model_copy(update={"cases": ()})
    with pytest.raises(DeliberationInputError):
        start_session(broken, CASE)


def test_history_requires_contiguous_numbers_and_closed_prior_rounds():
    state = apply(fresh(), "restart", {"case_id": CASE}).model_dump(mode="json")
    for field, value in [("number", 3), ("closed_reason", "none")]:
        invalid = copy.deepcopy(state)
        invalid["rounds"][0][field] = value
        with pytest.raises(DeliberationInputError):
            validate_session(encode(invalid), PACK)


def test_injected_decision_without_reveal_is_rejected():
    data = fresh().model_dump(mode="json")
    data["rounds"][0]["decision"] = choice()
    with pytest.raises(DeliberationInputError):
        validate_session(encode(data), PACK)


def test_types_immutable_and_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        fresh().authority = "allowed"
    with pytest.raises(ValidationError):
        DeliberationPack.model_validate({**json.loads(RAW), "auto_approve": True})
    with pytest.raises(ValidationError):
        DeliberationSession.model_validate({**fresh().model_dump(), "credential": "nurse"})
