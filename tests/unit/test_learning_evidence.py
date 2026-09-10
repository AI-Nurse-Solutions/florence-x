"""SS-02 contract and admission tests. No external retrieval, LLM or clinical data."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest
from florence_core.schemas.learning_evidence import (
    EvidenceInputError,
    EvidenceRequest,
    PackAdmission,
    inspect_evidence,
    load_admitted_evidence,
    parse_evidence,
)
from florence_core.schemas.mission import mission_digest, parse_workspace

ROOT = Path(__file__).resolve().parents[2]
RAW = (ROOT / "examples/learning_evidence/public-pack.json").read_bytes()
ADMISSION = PackAdmission.model_validate_json((ROOT / "examples/learning_evidence/admission.json").read_bytes())
NOW = datetime(2026, 9, 10, 5, 0, tzinfo=UTC)


def source():
    return json.loads(RAW)


def request():
    return EvidenceRequest.model_validate(ADMISSION.model_dump(exclude={"raw_sha256"}))


def test_admitted_pack_bound_to_original_mission():
    reader = Mock(return_value=RAW)
    p = load_admitted_evidence(request(), ADMISSION, reader)
    reader.assert_called_once_with()
    mission = parse_workspace((ROOT / "examples/portable_learning/workspace.json").read_bytes()).mission
    assert p.mission_id == mission.mission_id
    assert p.mission_sha256 == mission_digest(mission)
    assert parse_evidence(p.model_dump_json().encode()) == p


def test_four_claim_kinds_and_honest_support():
    result = inspect_evidence(parse_evidence(RAW), as_of=NOW)
    assert {c["kind"] for c in result["claims"]} == {"retrieved_evidence", "generated_synthesis", "inference", "missing_information"}
    by_id = {c["claim_id"]: c for c in result["claims"]}
    assert by_id["quote-nist-scope"]["status"] == "quoted_excerpt_match"
    assert by_id["synthesis-check"]["status"] == "linked_not_verified"
    assert by_id["exercise-unsupported"]["status"] == "unsupported_no_passage"
    assert by_id["gap-outcomes"]["status"] == "missing_information"
    assert all(c["semantic_support"] == "not_assessed" for c in result["claims"])
    assert result["human_learning"] == "not_evaluated"
    assert result["authorization"] == "no_execution_interface"


@pytest.mark.parametrize("field,value", [
    ("pack_id", "private-pack"), ("version", "9.0.0"), ("mission_id", "another-mission"),
    ("mission_sha256", "0" * 64), ("data_classification", "internal"),
    ("data_classification", "phi_local"), ("purpose", "clinical_execution"),
])
def test_selection_refused_before_reader(field, value):
    invalid = request().model_copy(update={field: value})
    reader = Mock(return_value=RAW)
    with pytest.raises(EvidenceInputError):
        load_admitted_evidence(invalid, ADMISSION, reader)
    reader.assert_not_called()


def test_admission_cannot_be_copied_to_private_scope():
    reader = Mock(return_value=RAW)
    with pytest.raises(EvidenceInputError):
        load_admitted_evidence(request(), ADMISSION.model_copy(update={"data_classification": "internal"}), reader)
    reader.assert_not_called()


@pytest.mark.parametrize("raw", [RAW + b" ", b"", b"a" * 131073, "not bytes"])
def test_changed_or_oversized_package_not_returned(raw):
    with pytest.raises(EvidenceInputError):
        load_admitted_evidence(request(), ADMISSION, Mock(return_value=raw))


def test_reader_error_is_sanitized():
    reader = Mock(side_effect=OSError("PRIVATE_PATH_MARKER"))
    with pytest.raises(EvidenceInputError) as e:
        load_admitted_evidence(request(), ADMISSION, reader)
    assert "PRIVATE_PATH_MARKER" not in str(e.value)


def test_body_must_match_admission_even_if_raw_hash_matches():
    data = source()
    data["mission_id"] = "another-mission"
    raw = json.dumps(data).encode()
    admitted = ADMISSION.model_copy(update={"raw_sha256": hashlib.sha256(raw).hexdigest()})
    with pytest.raises(EvidenceInputError):
        load_admitted_evidence(request(), admitted, Mock(return_value=raw))


@pytest.mark.parametrize("raw", [b"", b"null", b"[]", b"{}", b"{", b"\xff",
    b'{"schema_version":"0.1.0","schema_version":"0.1.0"}', b'{"x":NaN}',
    b'{"x":Infinity}', b"[" * 1500 + b"]" * 1500, b"a" * 131073])
def test_bad_json_has_generic_error(raw):
    with pytest.raises(EvidenceInputError) as e:
        parse_evidence(raw)
    assert str(e.value) == "Invalid public evidence pack; nothing was activated."


@pytest.mark.parametrize("field,value", [
    ("data_classification", "internal"), ("data_classification", None), ("version", "latest"),
    ("schema_version", "2.0.0"), ("passages", []), ("claims", []),
    ("pillar_dependencies", ["judgment"]), ("tool", "terminal"),
    ("approval", "granted"), ("ai_assistance", {"used": False}),
])
def test_invalid_pack_fields(field, value):
    data = source()
    data[field] = value
    with pytest.raises(EvidenceInputError):
        parse_evidence(json.dumps(data).encode())


@pytest.mark.parametrize("field,value", [
    ("captured_at", "2026-09-09T12:00:00"), ("hash_scope", "full_document"),
    ("evidence_certainty", "high"), ("recommendation_strength", "strong"),
    ("rights_note", ""), ("review_due_at", "2020-01-01T00:00:00Z"),
])
def test_invalid_passage_metadata(field, value):
    data = source()
    data["passages"][0][field] = value
    with pytest.raises(EvidenceInputError):
        parse_evidence(json.dumps(data).encode())


def test_nonpublic_source_refused():
    data = source()
    data["passages"][0]["source"]["data_classification"] = "internal"
    with pytest.raises(EvidenceInputError):
        parse_evidence(json.dumps(data).encode())


@pytest.mark.parametrize("collection", ["passages", "claims", "glossary"])
def test_duplicate_identifiers_refused(collection):
    data = source()
    data[collection][1] = data[collection][0]
    with pytest.raises(EvidenceInputError):
        parse_evidence(json.dumps(data).encode())


def test_glossary_reference_must_resolve():
    data = source()
    data["glossary"][0]["passage_ids"] = ["absent"]
    with pytest.raises(EvidenceInputError):
        parse_evidence(json.dumps(data).encode())


@pytest.mark.parametrize("field,value,state", [
    ("passage", "absent", "reference_missing"), ("source_id", "absent", "reference_missing"),
    ("expected_revision", "older", "revision_changed"),
    ("expected_excerpt_sha256", "0" * 64, "excerpt_changed"),
])
def test_bad_claim_references_remain_visible(field, value, state):
    data = source()
    data["claims"][0]["citations"][0][field] = value
    result = inspect_evidence(data, as_of=NOW)
    c = result["claims"][0]
    assert c["status"] == "needs_attention"
    assert c["links"][0]["state"] == state
    assert c["semantic_support"] == "not_assessed"


def test_changed_actual_passage_does_not_keep_integrity_badge():
    data = source()
    data["passages"][0]["quote"] += " changed"
    result = inspect_evidence(data, as_of=NOW)
    assert result["passages"][0]["integrity"] == "excerpt_changed"
    assert result["claims"][0]["status"] == "needs_attention"


def test_misquoted_evidence_is_not_an_exact_excerpt():
    data = source()
    data["claims"][0]["statement"] = "Unsupported replacement text"
    assert inspect_evidence(data, as_of=NOW)["claims"][0]["status"] == "quote_text_mismatch"


def test_linked_false_interpretation_never_earns_verified_support():
    data = source()
    data["claims"][3]["statement"] = "Citations guarantee that every answer is safe."
    c = inspect_evidence(data, as_of=NOW)["claims"][3]
    assert c["status"] == "linked_not_verified"
    assert c["semantic_support"] == "not_assessed"


def test_overdue_and_future_excerpts_visible():
    pack = parse_evidence(RAW)
    assert inspect_evidence(pack, as_of=NOW + timedelta(days=365))["passages"][0]["currency"] == "review_due"
    assert inspect_evidence(pack, as_of=NOW - timedelta(days=365))["claims"][0]["links"][0]["state"] == "future_capture"


@pytest.mark.parametrize("as_of", [None, "2026-09-10", NOW.replace(tzinfo=None)])
def test_invalid_inspection_time_rejected(as_of):
    with pytest.raises(EvidenceInputError):
        inspect_evidence(parse_evidence(RAW), as_of=as_of)


def test_copied_model_revalidated():
    pack = parse_evidence(RAW)
    with pytest.raises(EvidenceInputError):
        inspect_evidence(pack.model_copy(update={"data_classification": "internal"}), as_of=NOW)


def test_inspection_does_not_mutate_canonical_records():
    pack = parse_evidence(RAW)
    before = pack.model_dump_json()
    inspect_evidence(pack, as_of=NOW)
    assert before == pack.model_dump_json()


def test_excerpts_have_bounded_reuse_and_explicit_scope():
    for p in parse_evidence(RAW).passages:
        assert len(p.quote.split()) <= 25
        assert p.hash_scope == "quoted_excerpt_utf8"
        assert p.rights_note and p.inspection_scope and p.limitations
        assert hashlib.sha256(p.quote.encode()).hexdigest() == p.source.content_sha256
