"""H-003 non-executable catalog contracts; declarations never grant authority."""
from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, ConfigDict, Field, StringConstraints, model_validator

from .common import FlorenceModel
from .enums import DataClass

Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_.-]{0,95}$")]
Version = Annotated[str, StringConstraints(pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$",
                                            max_length=32)]
Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Pillar = Literal["knowledge", "judgment", "capability", "contribution"]


class CatalogRecord(FlorenceModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always",
                              validate_default=True, hide_input_in_errors=True)


class CatalogSource(CatalogRecord):
    source_id: Identifier
    revision: Text
    content_sha256: Digest
    locator: Text  # An inert reference, not an instruction to retrieve a URL/path.
    origin: Literal["public_source", "synthetic_fixture"]
    data_classification: Literal[DataClass.PUBLIC]
    applicability: Text


class CatalogCitation(CatalogRecord):
    source_id: Identifier
    passage: Text


class CatalogClaim(CatalogRecord):
    claim_id: Identifier
    kind: Literal["retrieved_evidence", "generated_synthesis", "inference", "missing_information"]
    statement: Text
    citations: tuple[CatalogCitation, ...] = Field(default=(), max_length=32)

    @model_validator(mode="after")
    def check_citations(self) -> Self:
        if self.kind == "retrieved_evidence" and not self.citations:
            raise ValueError("retrieved evidence needs a passage reference")
        if self.kind == "missing_information" and self.citations:
            raise ValueError("missing information cannot claim passage support")
        return self


class CatalogAIAssistance(CatalogRecord):
    used: bool = Field(strict=True)
    method: Text | None = None

    @model_validator(mode="after")
    def check_disclosure(self) -> Self:
        if self.used != (self.method is not None):
            raise ValueError("AI assistance and method disclosure must agree")
        return self


class CatalogArtifact(CatalogRecord):
    artifact_id: Identifier
    version: Version
    title: Text
    purpose: Text
    intended_users: tuple[Text, ...] = Field(min_length=1, max_length=16)
    owner_ref: Identifier
    primary_pillar: Pillar
    pillar_dependencies: tuple[Pillar, ...] = Field(min_length=1, max_length=3)
    data_classification: Literal[DataClass.PUBLIC]
    origin: Literal["public_source", "synthetic_fixture"]
    kind: Literal["learning_guide", "evidence_note", "reflection_template"]
    media_type: Literal["text/plain", "text/markdown"]
    content_sha256: Digest
    created_at: AwareDatetime
    publication_state: Literal["draft", "published", "withdrawn"] = "draft"
    sources: tuple[CatalogSource, ...] = Field(min_length=1, max_length=32)
    claims: tuple[CatalogClaim, ...] = Field(min_length=1, max_length=64)
    limitations: tuple[Text, ...] = Field(min_length=1, max_length=16)
    rights_note: Text
    ai_assistance: CatalogAIAssistance

    @model_validator(mode="after")
    def check_links(self) -> Self:
        dependencies = self.pillar_dependencies
        if self.primary_pillar in dependencies or len(set(dependencies)) != len(dependencies):
            raise ValueError("pillar dependencies must be distinct and exclude the primary pillar")
        source_ids = [s.source_id for s in self.sources]
        claim_ids = [c.claim_id for c in self.claims]
        if len(set(source_ids)) != len(source_ids) or len(set(claim_ids)) != len(claim_ids):
            raise ValueError("source and claim identities must be unique within an artifact")
        if any(c.source_id not in source_ids for claim in self.claims for c in claim.citations):
            raise ValueError("citation does not resolve to a declared source")
        if any(c.kind == "generated_synthesis" for c in self.claims) and not self.ai_assistance.used:
            raise ValueError("generated synthesis requires AI-assistance disclosure")
        return self

    def record_digest(self) -> str:
        """Bind all definition fields, including source snapshots and payload hash.

        Deterministic JSON for this contract, not a signature or general-purpose
        cross-language canonicalization standard. Truth is not proved by a hash.
        """
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True,
                             separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CatalogReview(CatalogRecord):
    """Declared content-review metadata, NOT a runtime HumanReview/ApprovalRecord."""

    review_id: Identifier
    artifact_id: Identifier
    artifact_version: Version
    artifact_record_sha256: Digest
    reviewer_ref: Identifier
    outcome: Literal["accepted_within_scope", "changes_requested"]
    scope: Text
    reviewed_at: AwareDatetime
    review_due_at: AwareDatetime
    evidence_refs: tuple[Identifier, ...] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def check_dates(self) -> Self:
        if self.review_due_at <= self.reviewed_at:
            raise ValueError("review due date must follow the review date")
        return self


class CatalogManifest(CatalogRecord):
    contract_version: Literal["0.1.0"]
    catalog_id: Identifier
    artifacts: tuple[CatalogArtifact, ...] = Field(min_length=1, max_length=100)
    reviews: tuple[CatalogReview, ...] = Field(default=(), max_length=400)

    @model_validator(mode="after")
    def check_reviews(self) -> Self:
        artifacts = {(a.artifact_id, a.version): a for a in self.artifacts}
        if len(artifacts) != len(self.artifacts):
            raise ValueError("duplicate artifact id/version")
        ids: set[str] = set()
        times: set[tuple] = set()
        for review in self.reviews:
            key = (review.artifact_id, review.artifact_version)
            artifact = artifacts.get(key)
            if artifact is None or artifact.record_digest() != review.artifact_record_sha256:
                raise ValueError("review is not bound to the exact artifact definition")
            if review.reviewed_at < artifact.created_at:
                raise ValueError("review predates the artifact")
            time_key = (*key, review.reviewed_at)
            if review.review_id in ids or time_key in times:
                raise ValueError("duplicate review id or ambiguous review chronology")
            ids.add(review.review_id)
            times.add(time_key)
        return self
