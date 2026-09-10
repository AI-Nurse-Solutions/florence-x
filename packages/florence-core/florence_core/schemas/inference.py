"""SS-05A inference contracts for OFFLINE fixtures, not credentials or live transport."""
from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, StringConstraints, model_validator

from .catalog import CatalogRecord, CatalogSource, Digest, Identifier, Text, Version

Content = Annotated[str, StringConstraints(min_length=1, max_length=8000, strict=True)]
Count = Annotated[int, Field(strict=True, ge=0, le=1000000)]
Feature = Literal["text", "structured_output", "tool_proposals", "image_input", "streaming"]
Placement = Literal["device", "personal_cloud", "external_provider"]
ERROR = "Invalid offline inference record; no model or network operation performed."


def fingerprint(record: CatalogRecord) -> str:
    """Deterministic contract digest, not a signature or content-truth assessment."""
    raw = json.dumps(record.model_dump(mode="json"), sort_keys=True,
                     ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(ERROR)
        obj[key] = value
    return obj


def _constant(_):
    raise ValueError(ERROR)


def parse_record[T: CatalogRecord](raw: bytes, model: type[T]) -> T:
    """Bounded, duplicate-key rejecting entrypoint with input-free errors."""
    try:
        if type(raw) is not bytes or not 0 < len(raw) <= 65536:
            raise ValueError(ERROR)
        decoded = json.loads(raw, object_pairs_hook=_unique, parse_constant=_constant)
        return model.model_validate(decoded)
    except (ValueError, TypeError, RecursionError):
        raise ValueError(ERROR) from None


class ContextSpan(CatalogRecord):
    passage_id: Identifier
    source: CatalogSource
    excerpt: Content

    @model_validator(mode="after")
    def exact_text(self) -> Self:
        if hashlib.sha256(self.excerpt.encode()).hexdigest() != self.source.content_sha256:
            raise ValueError("excerpt differs from pinned source span")
        return self


class InferenceRequest(CatalogRecord):
    schema_version: Literal["0.1.0"]
    request_id: Identifier
    mission_id: Identifier
    mission_sha256: Digest
    task_id: Identifier
    task: Content
    context: tuple[ContextSpan, ...] = Field(min_length=1, max_length=8)
    data_classification: Literal["public"]
    purpose: Literal["professional_learning"]
    execution_mode: Literal["offline_fixture"]
    output_contract: Literal["resource_review_v1"]
    required_features: tuple[Feature, ...] = Field(min_length=1, max_length=5)
    max_output_tokens: int = Field(strict=True, ge=1, le=4096)
    max_output_bytes: int = Field(strict=True, ge=1, le=16000)
    timeout_ms: int = Field(strict=True, ge=1, le=120000)
    requested_profile: Identifier | None = None

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if len(set(self.required_features)) != len(self.required_features):
            raise ValueError("duplicate required feature")
        if "structured_output" not in self.required_features:
            raise ValueError("review output requires structured_output")
        if len({s.passage_id for s in self.context}) != len(self.context):
            raise ValueError("duplicate passage identity")
        return self


class FixtureModelProfile(CatalogRecord):
    profile_id: Identifier
    version: Version
    adapter: Literal["text_fixture_v1", "object_fixture_v1"]
    simulated_placement: Placement
    actual_execution: Literal["in_memory_fixture"]
    capabilities: tuple[Feature, ...] = Field(min_length=1, max_length=5)
    max_context_bytes: int = Field(strict=True, ge=1, le=65536)
    max_output_tokens: int = Field(strict=True, ge=1, le=4096)
    suitability: Literal["fixture_contract_only", "not_evaluated"]
    cost_units: Count
    latency_ms: Count
    estimates_basis: Literal["invented_fixture_values_not_model_performance"]

    @model_validator(mode="after")
    def unique_features(self) -> Self:
        if len(set(self.capabilities)) != len(self.capabilities):
            raise ValueError("duplicate model feature")
        return self


class OfflineAdmission(CatalogRecord):
    """Explicit test input only. No authenticated actor or deployment permission."""
    admission_id: Identifier
    scope: Literal["offline_fixture_only"]
    authority: Literal["no_deployment_authority"]
    policy_ref: Literal["fixture-routing-rules.0.1.0"]
    disposition: Literal["allow_fixture", "deny"]
    request_sha256: Digest
    profile_sha256s: tuple[Digest, ...] = Field(min_length=1, max_length=16)
    destinations: tuple[Placement, ...] = Field(min_length=1, max_length=3)
    valid_from: AwareDatetime
    expires_at: AwareDatetime
    max_cost_units: Count
    max_attempts: int = Field(strict=True, ge=1, le=1)

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.expires_at <= self.valid_from:
            raise ValueError("invalid admission validity window")
        if len(set(self.profile_sha256s)) != len(self.profile_sha256s):
            raise ValueError("duplicate admitted profile")
        if len(set(self.destinations)) != len(self.destinations):
            raise ValueError("duplicate admitted destination")
        # Literal equality alone can accept True as 1; require a real integer.
        if type(self.max_attempts) is not int:
            raise ValueError("attempt budget requires an integer")
        return self


class RoutePlan(CatalogRecord):
    status: Literal["eligible_fixture", "denied"]
    reason: Literal["eligible", "missing_admission", "invalid_admission", "outside_window",
                    "request_mismatch", "fixture_denied", "no_eligible_profile", "invalid_catalog"]
    request_sha256: Digest
    selected_profile: FixtureModelProfile | None = None
    selected_profile_sha256: Digest | None = None
    authority: Literal["no_deployment_authority"] = "no_deployment_authority"
    automatic_fallback: Literal["disabled"] = "disabled"

    @model_validator(mode="after")
    def consistency(self) -> Self:
        if self.status == "eligible_fixture":
            if self.reason != "eligible" or self.selected_profile is None:
                raise ValueError("eligible selection requires a profile")
            if self.selected_profile_sha256 != fingerprint(self.selected_profile):
                raise ValueError("profile digest mismatch")
        elif self.reason == "eligible" or self.selected_profile is not None or self.selected_profile_sha256 is not None:
            raise ValueError("denied selection must not name an executable target")
        return self


class ReviewProposal(CatalogRecord):
    summary: Text
    limitations: tuple[Text, ...] = Field(min_length=1, max_length=8)
    cited_passages: tuple[Identifier, ...] = Field(min_length=1, max_length=8)
    semantic_support: Literal["not_verified"]
    review_status: Literal["not_independently_reviewed"]


class FixtureUsage(CatalogRecord):
    output_tokens: Count
    elapsed_ms: Count
    cost_units: Count
    basis: Literal["invented_fixture_values_not_model_performance"]


class InferenceResult(CatalogRecord):
    request_sha256: Digest
    mission_sha256: Digest
    profile_sha256: Digest | None
    outcome: Literal["proposal_ready", "denied", "refused", "timed_out", "cancelled",
                     "unavailable", "invalid_response", "budget_exceeded"]
    proposal: ReviewProposal | None = None
    usage: FixtureUsage | None = None
    attempts: int = Field(strict=True, ge=0, le=1)
    actual_execution: Literal["in_memory_fixture"] = "in_memory_fixture"
    next_action: Literal["human_review", "stop_no_fallback"]
    authority: Literal["no_execution_permission"] = "no_execution_permission"

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.outcome == "proposal_ready":
            if self.proposal is None or self.usage is None or self.next_action != "human_review":
                raise ValueError("proposal result requires evidence and human review")
        elif self.proposal is not None or self.next_action != "stop_no_fallback":
            raise ValueError("non-success cannot retain a proposal or request automatic fallback")
        if self.attempts == 0 and (self.profile_sha256 is not None or self.outcome != "denied"):
            raise ValueError("no attempt must be a denied, unselected request")
        return self
