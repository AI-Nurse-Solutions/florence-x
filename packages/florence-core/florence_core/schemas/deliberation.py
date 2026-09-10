"""SS-03 nonclinical practice records; a learning choice is never permission.

Pure validation and transitions only. No persistence, model, network or identity
verification. Records are bounded and revalidated; this is not a tamper-proof log.
"""
from __future__ import annotations

import hashlib
import json
from typing import Literal, Self

from pydantic import Field, model_validator

from .catalog import CatalogRecord, Digest, Identifier, Text, Version
from .mission import _no_constant, _unique_object

Choice = Literal["accept", "revise", "reject", "withhold"]
CloseReason = Literal["none", "restarted", "context_changed", "evidence_view_changed"]


class PracticeCase(CatalogRecord):
    case_id: Identifier
    version: Version
    kind: Literal["omission", "competing_findings", "unsupported_certainty"]
    title: Text
    question: Text
    observations: tuple[Text, ...] = Field(min_length=1, max_length=5)
    proposal: Text
    proposal_disclosure: Literal["prepared_ai_assisted_fixture_not_live_model"]
    passage_ids: tuple[Identifier, ...] = Field(min_length=1, max_length=5)
    limitations: tuple[Text, ...] = Field(min_length=1, max_length=5)
    origin: Literal["synthetic_fixture"]

    @model_validator(mode="after")
    def unique_passages(self) -> Self:
        if len(set(self.passage_ids)) != len(self.passage_ids):
            raise ValueError("duplicate passage")
        return self


class DeliberationPack(CatalogRecord):
    schema_version: Literal["0.1.0"]
    pack_id: Identifier
    version: Version
    mission_id: Identifier
    mission_sha256: Digest
    evidence_pack_id: Identifier
    evidence_version: Version
    evidence_raw_sha256: Digest
    data_classification: Literal["public"]
    cases: tuple[PracticeCase, ...] = Field(min_length=3, max_length=3)
    limitations: tuple[Text, ...] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def cases_are_distinct(self) -> Self:
        if len({c.case_id for c in self.cases}) != len(self.cases):
            raise ValueError("duplicate case")
        if {c.kind for c in self.cases} != {"omission", "competing_findings", "unsupported_certainty"}:
            raise ValueError("missing exercise type")
        return self


def digest_record(record: CatalogRecord) -> str:
    checked = type(record).model_validate(record)
    text = json.dumps(checked.model_dump(mode="json"), sort_keys=True,
                      ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class InitialInterpretation(CatalogRecord):
    text: Text | None = None
    uncertain: bool = Field(strict=True)

    @model_validator(mode="after")
    def interpretation_or_uncertainty(self) -> Self:
        if self.text is None and not self.uncertain:
            raise ValueError("interpretation or explicit uncertainty required")
        return self


class LearningChoice(CatalogRecord):
    outcome: Choice
    reason: Text
    alternative: Text
    consequence: Text
    replacement: Text | None = None

    @model_validator(mode="after")
    def revision_is_explicit(self) -> Self:
        if (self.outcome == "revise") != (self.replacement is not None):
            raise ValueError("replacement belongs to revision only")
        return self


class ComparisonRound(CatalogRecord):
    number: int = Field(strict=True, ge=1, le=12)
    case: PracticeCase
    context_sha256: Digest
    initial: InitialInterpretation | None = None
    revealed: bool = Field(default=False, strict=True)
    decision: LearningChoice | None = None
    reflection: Text | None = None
    closed_reason: CloseReason = "none"

    @model_validator(mode="after")
    def ordered_and_bound(self) -> Self:
        if self.context_sha256 != digest_record(self.case):
            raise ValueError("context changed")
        if self.revealed and self.initial is None:
            raise ValueError("reveal requires initial interpretation")
        if self.decision is not None and not self.revealed:
            raise ValueError("choice requires comparison")
        if self.reflection is not None and self.decision is None:
            raise ValueError("reflection requires a learning choice")
        return self


class DeliberationSession(CatalogRecord):
    schema_version: Literal["0.1.0"] = "0.1.0"
    session_id: Literal["practice.local.session"] = "practice.local.session"
    mission_id: Identifier
    mission_sha256: Digest
    pack_sha256: Digest
    scope: Literal["nonclinical_practice"] = "nonclinical_practice"
    persistence: Literal["memory_only"] = "memory_only"
    actor_status: Literal["not_authenticated"] = "not_authenticated"
    authority: Literal["no_execution_permission"] = "no_execution_permission"
    paused: bool = Field(default=False, strict=True)
    rounds: tuple[ComparisonRound, ...] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def ordered_history(self) -> Self:
        if [r.number for r in self.rounds] != list(range(1, len(self.rounds) + 1)):
            raise ValueError("round sequence invalid")
        if any(r.closed_reason == "none" for r in self.rounds[:-1]):
            raise ValueError("only last round may be open")
        return self


class DeliberationInputError(ValueError):
    """A public error with no learner text, source bytes or identity."""


def _fail() -> DeliberationInputError:
    return DeliberationInputError("Invalid or out-of-order practice request; nothing changed.")


def parse_pack(raw: bytes) -> DeliberationPack:
    try:
        if not isinstance(raw, bytes) or not 0 < len(raw) <= 65536:
            raise ValueError("input size")
        return DeliberationPack.model_validate(json.loads(raw.decode("utf-8"),
            object_pairs_hook=_unique_object, parse_constant=_no_constant))
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise _fail() from None


def validate_session(raw: bytes, pack: DeliberationPack) -> DeliberationSession:
    """Validate a memory snapshot against an application-owned fixture pack."""
    try:
        pack = DeliberationPack.model_validate(pack)
        if not isinstance(raw, bytes) or not 0 < len(raw) <= 262144:
            raise ValueError("input size")
        session = DeliberationSession.model_validate(json.loads(raw.decode("utf-8"),
            object_pairs_hook=_unique_object, parse_constant=_no_constant))
        if (session.mission_id, session.mission_sha256, session.pack_sha256) != (
                pack.mission_id, pack.mission_sha256, digest_record(pack)):
            raise ValueError("wrong mission or pack")
        cases = {c.case_id: c for c in pack.cases}
        if any(r.case != cases.get(r.case.case_id) for r in session.rounds):
            raise ValueError("unknown or changed context")
        return session
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise _fail() from None


def _checked(session: DeliberationSession, pack: DeliberationPack) -> DeliberationSession:
    try:
        clean = DeliberationSession.model_validate(session)
        return validate_session(clean.model_dump_json().encode("utf-8"), pack)
    except (ValueError, TypeError, AttributeError):
        raise _fail() from None


def start_session(pack: DeliberationPack, case_id: str) -> DeliberationSession:
    try:
        pack = DeliberationPack.model_validate(pack)
        case = next(c for c in pack.cases if c.case_id == case_id)
        return DeliberationSession(mission_id=pack.mission_id, mission_sha256=pack.mission_sha256,
            pack_sha256=digest_record(pack), rounds=(ComparisonRound(number=1, case=case,
                context_sha256=digest_record(case)),))
    except (ValueError, TypeError, StopIteration):
        raise _fail() from None


def transition(session: DeliberationSession, pack: DeliberationPack,
               action: str, payload: dict | None = None) -> DeliberationSession:
    """Return a new bounded practice snapshot. No side effects or authority.

    A context change closes the active round without overwriting its decisions.
    Restart is explicit and never means delete. Clear is a separate UI operation.
    """
    try:
        current = _checked(session, pack)
        if payload is None:
            payload = {}
        if type(payload) is not dict:
            raise ValueError("payload")
        data = current.model_dump(mode="json")
        r = data["rounds"][-1]
        if action == "pause":
            if payload:
                raise ValueError("unexpected fields")
            data["paused"] = not data["paused"]
        elif action == "invalidate":
            if set(payload) != {"reason"} or payload["reason"] not in {"context_changed", "evidence_view_changed"}:
                raise ValueError("invalidation reason")
            if r["closed_reason"] == "none":
                r["closed_reason"] = payload["reason"]
        else:
            if current.paused:
                raise ValueError("paused")
            if action == "restart":
                if set(payload) != {"case_id"} or len(data["rounds"]) >= 12:
                    raise ValueError("restart or budget")
                case = next(c for c in pack.cases if c.case_id == payload["case_id"])
                if r["closed_reason"] == "none":
                    r["closed_reason"] = "restarted"
                data["rounds"].append(ComparisonRound(number=len(data["rounds"])+1, case=case,
                    context_sha256=digest_record(case)).model_dump(mode="json"))
            else:
                if r["closed_reason"] != "none":
                    raise ValueError("stale context")
                if action == "commit" and r["initial"] is None:
                    r["initial"] = InitialInterpretation.model_validate(payload).model_dump(mode="json")
                elif action == "reveal" and r["initial"] is not None and not r["revealed"] and not payload:
                    r["revealed"] = True
                elif action == "choose" and r["revealed"] and r["decision"] is None:
                    r["decision"] = LearningChoice.model_validate(payload).model_dump(mode="json")
                elif action == "reflect" and r["decision"] is not None and r["reflection"] is None:
                    if set(payload) != {"text"}:
                        raise ValueError("reflection fields")
                    r["reflection"] = payload["text"]
                    if r["reflection"] is None:
                        raise ValueError("reflection required")
                else:
                    raise ValueError("invalid transition")
        return validate_session(json.dumps(data, ensure_ascii=False).encode("utf-8"), pack)
    except (ValueError, TypeError, StopIteration, AttributeError, RecursionError):
        raise _fail() from None
