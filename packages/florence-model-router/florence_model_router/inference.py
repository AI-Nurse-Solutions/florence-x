"""SS-05A offline admission, selection and response normalization. No transport.

This module cannot call a model. Fixture destinations and budgets are test inputs,
not evidence of hosting, performance, identity, EDENA approval or egress isolation.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Literal

from florence_core.schemas.catalog import CatalogRecord
from florence_core.schemas.inference import (
    FixtureModelProfile,
    FixtureUsage,
    InferenceRequest,
    InferenceResult,
    OfflineAdmission,
    ReviewProposal,
    RoutePlan,
    fingerprint,
    parse_record,
)
from pydantic import Field, model_validator


def _validated(record, cls):
    if type(record) is not cls:
        raise ValueError("Unexpected offline contract type")
    return parse_record(record.model_dump_json().encode(), cls)


def plan_inference(request: InferenceRequest, profiles: tuple[FixtureModelProfile, ...],
                   admission: OfflineAdmission | None, *, now: datetime) -> RoutePlan:
    request = _validated(request, InferenceRequest)
    request_hash = fingerprint(request)

    def denied(reason):
        return RoutePlan(status="denied", reason=reason, request_sha256=request_hash)

    if admission is None:
        return denied("missing_admission")
    try:
        admission = _validated(admission, OfflineAdmission)
    except ValueError:
        return denied("invalid_admission")
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        return denied("invalid_admission")
    if not admission.valid_from <= now < admission.expires_at:
        return denied("outside_window")
    if admission.disposition != "allow_fixture":
        return denied("fixture_denied")
    if admission.request_sha256 != request_hash:
        return denied("request_mismatch")
    try:
        if type(profiles) is not tuple or not 0 < len(profiles) <= 16:
            return denied("invalid_catalog")
        catalog = tuple(_validated(p, FixtureModelProfile) for p in profiles)
        if len({p.profile_id for p in catalog}) != len(catalog):
            return denied("invalid_catalog")
    except ValueError:
        return denied("invalid_catalog")
    size = len(request.model_dump_json().encode())
    admitted = [p for p in catalog
                if fingerprint(p) in admission.profile_sha256s
                and p.simulated_placement in admission.destinations
                and (request.requested_profile is None or request.requested_profile == p.profile_id)]
    capable = [p for p in admitted
               if set(request.required_features) <= set(p.capabilities)
               and p.suitability == "fixture_contract_only"
               and p.max_context_bytes >= size
               and p.max_output_tokens >= request.max_output_tokens
               and p.cost_units <= admission.max_cost_units
               and p.latency_ms <= request.timeout_ms]
    if not capable:
        return denied("no_eligible_profile")
    # These are invented comparison numbers, never a measured performance ranking.
    selected = min(capable, key=lambda p: (p.cost_units, p.latency_ms, p.profile_id))
    return RoutePlan(status="eligible_fixture", reason="eligible", request_sha256=request_hash,
                     selected_profile=selected, selected_profile_sha256=fingerprint(selected))


Status = Literal["ok", "refused", "timed_out", "cancelled", "unavailable"]


class TextFixtureEnvelope(CatalogRecord):
    """Invented test format; not an Ollama, OpenAI or other provider contract."""
    status: Status
    text: str | None = Field(default=None, max_length=16000)
    usage: FixtureUsage

    @model_validator(mode="after")
    def has_payload(self):
        if (self.status == "ok") != (self.text is not None):
            raise ValueError("fixture status and payload disagree")
        return self


class ObjectFixtureEnvelope(CatalogRecord):
    """Second invented test format with an object payload instead of encoded text."""
    state: Status
    review: ReviewProposal | None = None
    usage: FixtureUsage

    @model_validator(mode="after")
    def has_payload(self):
        if (self.state == "ok") != (self.review is not None):
            raise ValueError("fixture state and payload disagree")
        return self


class TextFixtureAdapter:
    @staticmethod
    def normalize(raw: bytes):
        env = parse_record(raw, TextFixtureEnvelope)
        review = parse_record(env.text.encode(), ReviewProposal) if env.text is not None else None
        return env.status, review, env.usage


class ObjectFixtureAdapter:
    @staticmethod
    def normalize(raw: bytes):
        env = parse_record(raw, ObjectFixtureEnvelope)
        return env.state, env.review, env.usage


# No user-supplied callbacks, dynamic imports, URL clients, credentials or model SDKs.
ADAPTERS = {"text_fixture_v1": TextFixtureAdapter, "object_fixture_v1": ObjectFixtureAdapter}


def replay_inference(request: InferenceRequest, profiles: tuple[FixtureModelProfile, ...],
                     admission: OfflineAdmission | None, wires: Mapping[str, bytes],
                     *, now: datetime) -> InferenceResult:
    """Recheck admission immediately before consuming ONE supplied fixture response.

    No precomputed plan is accepted as permission. No alternate adapter, automatic
    retry or fallback is attempted on any outcome. In-memory fixtures only.
    """
    request = _validated(request, InferenceRequest)
    plan = plan_inference(request, profiles, admission, now=now)
    common = {"request_sha256": plan.request_sha256, "mission_sha256": request.mission_sha256,
              "profile_sha256": plan.selected_profile_sha256,
              "attempts": 1 if plan.status == "eligible_fixture" else 0}

    def stopped(outcome, usage=None):
        return InferenceResult(**common, outcome=outcome, usage=usage, next_action="stop_no_fallback")

    if plan.status != "eligible_fixture":
        return stopped("denied")
    # Reparse the separately supplied admission; model fields never define permission.
    grant = _validated(admission, OfflineAdmission)
    profile = plan.selected_profile
    try:
        raw = wires[profile.profile_id]
    except KeyError:
        return stopped("unavailable")
    try:
        status, review, usage = ADAPTERS[profile.adapter].normalize(raw)
    except (ValueError, TypeError, UnicodeError):
        return stopped("invalid_response")
    if (usage.output_tokens > request.max_output_tokens or usage.elapsed_ms > request.timeout_ms
            or usage.cost_units > grant.max_cost_units):
        return stopped("budget_exceeded", usage)
    if status != "ok":
        return stopped(status, usage)
    known = {s.passage_id for s in request.context}
    if len(set(review.cited_passages)) != len(review.cited_passages):
        return stopped("invalid_response", usage)
    if not set(review.cited_passages) <= known:
        return stopped("invalid_response", usage)
    if len(review.model_dump_json().encode()) > request.max_output_bytes:
        return stopped("budget_exceeded", usage)
    return InferenceResult(**common, outcome="proposal_ready", proposal=review, usage=usage,
                           next_action="human_review")
