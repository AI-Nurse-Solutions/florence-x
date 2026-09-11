"""SS-06A private-envelope and OFFLINE save-evidence contracts. No writer or permit."""
from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, StringConstraints, ValidationInfo, field_validator, model_validator

from .catalog import CatalogArtifact, CatalogRecord, Digest, Identifier, Text, Version

Payload = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=16000)]


def digest(record: CatalogRecord) -> str:
    """Version-local deterministic digest, not a signature or a privacy guarantee."""
    raw = json.dumps(record.model_dump(mode="json"), sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class PortfolioEnvelope(CatalogRecord):
    schema_version: Literal["0.1.0"] = "0.1.0"
    mission_id: Identifier
    mission_sha256: Digest
    owner_ref: Identifier
    workspace_ref: Identifier
    destination_ref: Identifier  # Inert registered destination ID, never a path or URL.
    artifact: CatalogArtifact
    learning_decision_sha256: Digest  # Link only. LearningChoice is NOT save approval.
    purpose: Text
    audience: Literal["owner_only"] = "owner_only"
    contribution_state: Literal["not_submitted"] = "not_submitted"
    content_review: Literal["not_independently_reviewed"] = "not_independently_reviewed"
    competence: Literal["not_assessed"] = "not_assessed"

    @model_validator(mode="after")
    def private_draft(self) -> Self:
        if self.owner_ref != self.artifact.owner_ref or self.artifact.publication_state != "draft":
            raise ValueError("private draft owner or publication state mismatch")
        return self

    def logical_key(self) -> str:
        """Create-only identity; changed contents at the same target must conflict."""
        keys = [self.owner_ref, self.workspace_ref, self.destination_ref,
                self.artifact.artifact_id, self.artifact.version]
        return hashlib.sha256(json.dumps(keys, separators=(",", ":")).encode()).hexdigest()


class SaveFixture(CatalogRecord):
    origin: Literal["synthetic_fixture"] = "synthetic_fixture"
    mode: Literal["offline_contract_test"] = "offline_contract_test"
    authority: Literal["no_execution_permission"] = "no_execution_permission"

    @field_validator("overwrite", "storage_operations", "successful_receipt_issued",
                     mode="before", check_fields=False)
    @classmethod
    def no_coercion_of_disabled_controls(cls, value, info: ValidationInfo):
        expected = int if info.field_name == "storage_operations" else bool
        if type(value) is not expected or value != 0:
            raise ValueError("disabled control cannot be enabled or coerced")
        return value


class SaveIntentFixture(SaveFixture):
    intent_id: Identifier
    actor_ref: Identifier
    envelope_sha256: Digest
    logical_key: Digest
    capability_version: Version
    policy_ref: Identifier
    policy_version: Version
    operation: Literal["create_private_entry"] = "create_private_entry"
    overwrite: Literal[False] = False


class SavePolicyFixture(SaveFixture):
    intent_sha256: Digest
    policy_ref: Identifier
    policy_version: Version
    disposition: Literal["allow_in_simulation", "deny"]
    valid_from: AwareDatetime
    expires_at: AwareDatetime

    @model_validator(mode="after")
    def window(self) -> Self:
        if self.expires_at <= self.valid_from:
            raise ValueError("empty policy validity interval")
        return self


class SaveApprovalFixture(SaveFixture):
    intent_sha256: Digest
    policy_sha256: Digest
    approver_ref: Identifier
    disposition: Literal["confirm_in_simulation", "reject"]
    approved_at: AwareDatetime
    expires_at: AwareDatetime

    @model_validator(mode="after")
    def window(self) -> Self:
        if self.expires_at <= self.approved_at:
            raise ValueError("empty approval validity interval")
        return self


class SaveAttemptFixture(SaveFixture):
    operation_ref: Identifier
    intent_sha256: Digest
    policy_sha256: Digest
    approval_sha256: Digest
    logical_key: Digest
    envelope_sha256: Digest
    dispatched_at: AwareDatetime
    reported_state: Literal["in_flight", "reported_success", "reported_failure", "outcome_unknown"]
    audit_recorded: bool = Field(strict=True)


class SaveReadBackFixture(SaveFixture):
    operation_ref: Identifier
    observed_at: AwareDatetime
    state: Literal["found", "absent", "unavailable"]
    envelope: PortfolioEnvelope | None = None
    content_utf8: Payload | None = None

    @model_validator(mode="after")
    def evidence_shape(self) -> Self:
        if self.state == "found":
            if self.envelope is None or self.content_utf8 is None:
                raise ValueError("found requires full envelope and content")
        elif self.envelope is not None or self.content_utf8 is not None:
            raise ValueError("absent/unavailable must not claim a stored record")
        return self


class SaveScenario(SaveFixture):
    envelope: PortfolioEnvelope
    content_utf8: Payload
    intent: SaveIntentFixture
    policy: SavePolicyFixture | None = None
    approval: SaveApprovalFixture | None = None
    approval_revoked_at: AwareDatetime | None = None  # Scoped to this scenario's approval.
    audit_available_now: bool = Field(strict=True)
    as_of: AwareDatetime
    attempt: SaveAttemptFixture | None = None
    readback: SaveReadBackFixture | None = None


class SaveAssessment(SaveFixture):
    envelope_sha256: Digest
    current_guard_failures: tuple[str, ...]
    historical_guard_failures: tuple[str, ...]
    evidence_state: Literal["not_dispatched", "in_flight", "unknown", "absent_in_fixture",
                            "readback_mismatch", "readback_matches_fixture", "conflict"]
    next_step: Literal["blocked_no_dispatch", "fixture_ready_execution_disabled",
                       "reconcile_without_retry", "inspect_conflict_no_overwrite",
                       "inspect_matching_evidence_no_repeat"]
    storage_operations: Literal[0] = 0
    successful_receipt_issued: Literal[False] = False
    operational_saving: Literal["disabled"] = "disabled"
    real_persistence: Literal["not_observed"] = "not_observed"
