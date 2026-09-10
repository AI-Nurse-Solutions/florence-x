"""SS-01 portable learning records. Inspection only; never an authorization."""
from __future__ import annotations

import hashlib
import json
from typing import Literal, Self

from pydantic import AwareDatetime, Field, ValidationError, model_validator

from .catalog import CatalogRecord, CatalogSource, Digest, Identifier, Pillar, Text
from .enums import DataClass


class MissionRecord(CatalogRecord):
    schema_version: Literal["0.1.0"]
    mission_id: Identifier
    workspace_ref: Identifier
    owner_ref: Identifier  # Declared synthetic reference, not authenticated identity.
    purpose: Literal["professional_learning"]
    goal: Text
    success_criteria: tuple[Text, ...] = Field(min_length=1, max_length=8)
    data_classification: Literal[DataClass.PUBLIC]
    origin: Literal["public_source", "synthetic_fixture"]
    created_at: AwareDatetime
    revision: int = Field(strict=True, ge=1, le=1000000)
    record_state: Literal["draft"]
    stage: Literal["goal_identified"]
    primary_pillar: Literal["capability"]
    pillar_dependencies: tuple[Pillar, ...] = Field(min_length=3, max_length=3)
    sources: tuple[CatalogSource, ...] = Field(default=(), max_length=16)
    limitations: tuple[Text, ...] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def check_references(self) -> Self:
        if set(self.pillar_dependencies) != {"knowledge", "judgment", "contribution"}:
            raise ValueError("all other pillars must remain explicit")
        if len({s.source_id for s in self.sources}) != len(self.sources):
            raise ValueError("duplicate source identity")
        return self


class DeploymentLayout(CatalogRecord):
    interaction: Literal["device_browser"]
    harness: Literal["device", "personal_cloud"]
    authoritative_storage: Literal["device", "personal_cloud"]
    inference: Literal["device", "external_provider", "personal_cloud"]


# These are inert fixture references, NOT live URL allowlists or policy grants.
PROFILE_LAYOUTS = {
    "local": ("device", "device", "device", "fixture.local-model"),
    "hybrid": ("device", "device", "external_provider", "fixture.external-model"),
    "hosted_test": ("personal_cloud", "personal_cloud", "personal_cloud", "fixture.hosted-model"),
}


class DeploymentManifest(CatalogRecord):
    schema_version: Literal["0.1.0"]
    manifest_id: Identifier
    revision: int = Field(strict=True, ge=1, le=1000000)
    profile: Literal["local", "hybrid", "hosted_test"]
    label: Text
    target_layout: DeploymentLayout
    endpoint_ref: Literal["fixture.local-model", "fixture.external-model", "fixture.hosted-model"]
    mode: Literal["preview_only"]
    authority: Literal["not_authorized"]
    hermes: Literal["optional_not_connected"]
    inference_enabled: bool = Field(strict=True)
    persistence_enabled: bool = Field(strict=True)
    network_enabled: bool = Field(strict=True)
    data_classification: Literal[DataClass.PUBLIC]
    limits: tuple[Text, ...] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def check_preview(self) -> Self:
        layout = self.target_layout
        actual = (layout.harness, layout.authoritative_storage, layout.inference, self.endpoint_ref)
        if actual != PROFILE_LAYOUTS[self.profile]:
            raise ValueError("profile, locations and fixture endpoint disagree")
        if self.inference_enabled or self.persistence_enabled or self.network_enabled:
            raise ValueError("preview cannot enable processing, persistence or network access")
        return self


class WorkspaceBundle(CatalogRecord):
    schema_version: Literal["0.1.0"]
    mission: MissionRecord
    manifests: tuple[DeploymentManifest, ...] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def check_profiles(self) -> Self:
        if {m.profile for m in self.manifests} != set(PROFILE_LAYOUTS):
            raise ValueError("exactly one manifest per supported profile is required")
        if len({m.manifest_id for m in self.manifests}) != 3:
            raise ValueError("manifest identities must be distinct")
        return self


class MissionInputError(ValueError):
    """Public errors do not echo supplied content, identity, paths or endpoints."""


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _no_constant(_: str) -> None:
    raise ValueError("non-finite constant")


def parse_workspace(raw: bytes) -> WorkspaceBundle:
    """Bounded, exact JSON validation; no files, retrieval, models or network."""
    try:
        if not isinstance(raw, bytes) or not 0 < len(raw) <= 65536:
            raise ValueError("invalid input size or type")
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_no_constant)
        return WorkspaceBundle.model_validate(data)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise MissionInputError("Invalid portable workspace; no operation performed.") from None


def mission_digest(mission: MissionRecord) -> Digest:
    """Integrity comparison only. A digest is not authenticity, review or authority."""
    try:
        checked = MissionRecord.model_validate(mission)
        raw = json.dumps(checked.model_dump(mode="json"), sort_keys=True,
                         ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
    except (ValidationError, TypeError, ValueError):
        raise MissionInputError("Invalid mission; no operation performed.") from None


def inspect_profile(bundle: WorkspaceBundle, profile: str) -> dict:
    """Revalidate copied objects; profile comparison never migrates mission state."""
    try:
        checked = WorkspaceBundle.model_validate(bundle)
        if type(profile) is not str or profile not in PROFILE_LAYOUTS:
            raise ValueError("unsupported profile")
        manifest = next(m for m in checked.manifests if m.profile == profile)
        return {
            "mission_id": checked.mission.mission_id,
            "mission_sha256": mission_digest(checked.mission),
            "manifest": manifest.model_dump(mode="json"),
            "actual_processing": "none",
            "actual_storage": "none_by_this_library",
            "authorization": "not_assessed_no_execution_interface",
            "source_support": "not_assessed",
        }
    except (ValueError, TypeError, StopIteration):
        raise MissionInputError("Invalid profile inspection; no operation performed.") from None
