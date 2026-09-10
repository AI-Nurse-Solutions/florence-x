"""SS-02: bounded public evidence inspection. No model, network or execution.

Admission is supplied by the application, not the evidence document. Hashes bind
snapshots, not source truth or human identity. Interpretations stay unverified.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from typing import Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from .catalog import (
    CatalogAIAssistance,
    CatalogCitation,
    CatalogClaim,
    CatalogRecord,
    CatalogSource,
    Digest,
    Identifier,
    Text,
    Version,
)
from .enums import DataClass
from .mission import _no_constant, _unique_object


class EvidenceCitation(CatalogCitation):
    """The inherited passage field is a passage ID, not an arbitrary path."""
    passage: Identifier
    expected_revision: Text
    expected_excerpt_sha256: Digest


class EvidenceClaim(CatalogClaim):
    citations: tuple[EvidenceCitation, ...] = Field(default=(), max_length=8)
    limitation: Text


class EvidencePassage(CatalogRecord):
    passage_id: Identifier
    source: CatalogSource
    title: Text
    attribution: Text
    kind: Literal["guidance", "standard", "research_abstract"]
    quote: Text
    hash_scope: Literal["quoted_excerpt_utf8"]
    captured_at: AwareDatetime
    review_due_at: AwareDatetime
    rights_note: Text
    inspection_scope: Text
    limitations: tuple[Text, ...] = Field(min_length=1, max_length=6)
    evidence_certainty: Literal["not_appraised"] = "not_appraised"
    recommendation_strength: Literal["not_assigned"] = "not_assigned"

    @model_validator(mode="after")
    def check_dates_and_scope(self) -> Self:
        if self.review_due_at <= self.captured_at:
            raise ValueError("invalid inspection review dates")
        if self.source.origin != "public_source":
            raise ValueError("this source pack admits public primary excerpts only")
        return self


class GlossaryEntry(CatalogRecord):
    concept_id: Identifier
    label: Text
    definition: Text
    passage_ids: tuple[Identifier, ...] = Field(default=(), max_length=8)
    basis: Literal["source_linked_paraphrase", "project_working_definition"]
    review_status: Literal["not_independently_reviewed"] = "not_independently_reviewed"


class EvidencePack(CatalogRecord):
    schema_version: Literal["0.1.0"]
    pack_id: Identifier
    version: Version
    mission_id: Identifier
    mission_sha256: Digest
    data_classification: Literal[DataClass.PUBLIC]
    purpose: Literal["professional_learning"]
    primary_pillar: Literal["knowledge"]
    pillar_dependencies: tuple[Literal["judgment", "capability", "contribution"], ...]
    passages: tuple[EvidencePassage, ...] = Field(min_length=3, max_length=5)
    claims: tuple[EvidenceClaim, ...] = Field(min_length=1, max_length=24)
    glossary: tuple[GlossaryEntry, ...] = Field(min_length=1, max_length=16)
    ai_assistance: CatalogAIAssistance
    limitations: tuple[Text, ...] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def check_identity(self) -> Self:
        if set(self.pillar_dependencies) != {"judgment", "capability", "contribution"} or len(self.pillar_dependencies) != 3:
            raise ValueError("three other pillars required")
        for ids in ([p.passage_id for p in self.passages],
                    [p.source.source_id for p in self.passages],
                    [c.claim_id for c in self.claims], [g.concept_id for g in self.glossary]):
            if len(ids) != len(set(ids)):
                raise ValueError("duplicate identity")
        known = {p.passage_id for p in self.passages}
        if any(ref not in known for g in self.glossary for ref in g.passage_ids):
            raise ValueError("unresolved glossary reference")
        if any(g.basis == "source_linked_paraphrase" and not g.passage_ids for g in self.glossary):
            raise ValueError("source-linked glossary needs a passage")
        if any(c.kind == "generated_synthesis" for c in self.claims) and not self.ai_assistance.used:
            raise ValueError("synthesis requires AI disclosure")
        # Unresolved claim citations are retained for explicit diagnostic display.
        # No reference is promoted to verified semantic support by this parser.
        return self


class PackAdmission(CatalogRecord):
    """Code-controlled allowlist entry, not a human credential or EDENA decision."""
    pack_id: Identifier
    version: Version
    mission_id: Identifier
    mission_sha256: Digest
    raw_sha256: Digest
    data_classification: Literal[DataClass.PUBLIC]
    purpose: Literal["professional_learning"]


class EvidenceRequest(CatalogRecord):
    pack_id: Identifier
    version: Version
    mission_id: Identifier
    mission_sha256: Digest
    data_classification: Literal[DataClass.PUBLIC]
    purpose: Literal["professional_learning"]


class EvidenceInputError(ValueError):
    """Generic boundary errors never echo input content or supplied identifiers."""


def parse_evidence(raw: bytes) -> EvidencePack:
    try:
        if not isinstance(raw, bytes) or not 0 < len(raw) <= 131072:
            raise ValueError("invalid input")
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_no_constant)
        return EvidencePack.model_validate(data)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise EvidenceInputError("Invalid public evidence pack; nothing was activated.") from None


def load_admitted_evidence(request: EvidenceRequest, admission: PackAdmission,
                           reader: Callable[[], bytes]) -> EvidencePack:
    """Check selection before calling the fixed application's reader.

    The callback must read only the fixed package resource. No user-supplied URL
    or filesystem path reaches it. This is not protection from arbitrary Python.
    """
    try:
        requested = EvidenceRequest.model_validate(request)
        allowed = PackAdmission.model_validate(admission)
        for name in ("pack_id", "version", "mission_id", "mission_sha256", "data_classification", "purpose"):
            if getattr(requested, name) != getattr(allowed, name):
                raise ValueError("unadmitted selection")
        raw = reader()
        if not isinstance(raw, bytes) or len(raw) > 131072 or hashlib.sha256(raw).hexdigest() != allowed.raw_sha256:
            raise ValueError("changed package")
        pack = parse_evidence(raw)
        for name in ("pack_id", "version", "mission_id", "mission_sha256", "data_classification", "purpose"):
            if getattr(pack, name) != getattr(allowed, name):
                raise ValueError("package binding mismatch")
        return pack
    except (ValueError, TypeError, OSError, RecursionError):
        raise EvidenceInputError("Evidence selection refused; no evidence returned.") from None


def inspect_evidence(pack: EvidencePack, *, as_of: datetime) -> dict:
    """Return source excerpts plus diagnostics, never a clinical recommendation."""
    try:
        checked = EvidencePack.model_validate(pack)
        if not isinstance(as_of, datetime) or as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("inspection requires an aware timestamp")
        passages = {p.passage_id: p for p in checked.passages}
        passage_views = []
        for p in checked.passages:
            integrity = ("excerpt_match" if hashlib.sha256(p.quote.encode("utf-8")).hexdigest()
                         == p.source.content_sha256 else "excerpt_changed")
            timing = ("future_capture" if p.captured_at > as_of else
                      "review_due" if p.review_due_at <= as_of else "within_project_review_window")
            passage_views.append({**p.model_dump(mode="json"), "integrity": integrity, "currency": timing,
                                  "source_currency": "not_rechecked_online", "semantic_support": "not_assessed"})
        claims = []
        for c in checked.claims:
            links = []
            for ref in c.citations:
                p = passages.get(ref.passage)
                state = "reference_resolves"
                if p is None or p.source.source_id != ref.source_id:
                    state = "reference_missing"
                elif p.source.revision != ref.expected_revision:
                    state = "revision_changed"
                elif (hashlib.sha256(p.quote.encode("utf-8")).hexdigest() != ref.expected_excerpt_sha256
                      or p.source.content_sha256 != ref.expected_excerpt_sha256):
                    state = "excerpt_changed"
                elif p.captured_at > as_of:
                    state = "future_capture"
                elif p.review_due_at <= as_of:
                    state = "review_due"
                links.append({"passage_id": ref.passage, "state": state})
            if c.kind == "missing_information":
                status = "missing_information"
            elif not links:
                status = "unsupported_no_passage"
            elif any(link["state"] != "reference_resolves" for link in links):
                status = "needs_attention"
            elif c.kind == "retrieved_evidence":
                status = ("quoted_excerpt_match" if len(links) == 1 and c.statement == passages[links[0]["passage_id"]].quote
                          else "quote_text_mismatch")
            else:
                status = "linked_not_verified"
            claims.append({**c.model_dump(mode="json"), "status": status, "links": links,
                           "semantic_support": "not_assessed"})
        return {"pack_id": checked.pack_id, "version": checked.version,
                "mission_id": checked.mission_id, "mission_sha256": checked.mission_sha256,
                "as_of": as_of.isoformat(), "passages": passage_views, "claims": claims,
                "glossary": [g.model_dump(mode="json") for g in checked.glossary],
                "ai_assistance": checked.ai_assistance.model_dump(mode="json"),
                "limitations": list(checked.limitations), "authorization": "no_execution_interface",
                "professional_review": "not_independently_reviewed", "human_learning": "not_evaluated"}
    except (ValueError, TypeError, KeyError, RecursionError):
        raise EvidenceInputError("Invalid evidence inspection; no result returned.") from None
