"""Pure catalog inspection: no files, network, model calls, writes or execution.

The caller must supply already-permitted public metadata. Classification labels
are declarations, not data-loss prevention. Never log raw validation exceptions.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from pydantic import ValidationError

from .schemas.catalog import CatalogArtifact, CatalogManifest

MAX_MANIFEST_BYTES = 1_000_000
MAX_CONTENT_BYTES = 100_000


class CatalogValidationError(ValueError):
    """Sanitized failure at the catalog ingestion boundary."""


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    obj: dict = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate key")
        obj[key] = value
    return obj


def _reject_constant(value: str) -> None:
    raise ValueError("non-finite JSON constant")


def parse_catalog(raw: bytes) -> CatalogManifest:
    """Parse caller-supplied bytes, reject ambiguous JSON and sanitize errors."""
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_MANIFEST_BYTES:
        raise CatalogValidationError("Catalog input must be nonempty bytes within the size limit")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                          parse_constant=_reject_constant)
        return CatalogManifest.model_validate(data)
    except (ValueError, RecursionError):
        raise CatalogValidationError("Catalog metadata failed validation") from None


def _validated(catalog: CatalogManifest) -> CatalogManifest:
    try:
        return CatalogManifest.model_validate(catalog)
    except ValidationError:
        raise CatalogValidationError("Catalog metadata failed validation") from None


@dataclass(frozen=True)
class CatalogInspection:
    artifact: CatalogArtifact
    review_state: str
    warnings: tuple[str, ...]
    # Deliberately no run/approve/save flag: these are explanatory constants.
    authorization: str = "not_assessed_no_execution_interface"
    content_integrity: str = "not_checked"
    source_support: str = "linked_not_verified"


def inspect_artifact(catalog: CatalogManifest, artifact_id: str, version: str,
                     *, at: datetime) -> CatalogInspection:
    """Require an exact version and an explicit aware time; never imply latest."""
    if not isinstance(at, datetime) or at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("inspection time must be timezone-aware")
    catalog = _validated(catalog)
    artifact = next((a for a in catalog.artifacts
                     if a.artifact_id == artifact_id and a.version == version), None)
    if artifact is None:
        raise KeyError("exact artifact version not found")
    reviews = [r for r in catalog.reviews if r.artifact_id == artifact_id
               and r.artifact_version == version]
    effective = [r for r in reviews if r.reviewed_at <= at]
    review = max(effective, key=lambda r: r.reviewed_at) if effective else None
    state = "unreviewed"
    warnings = ["metadata_is_not_authorization", "source_support_not_verified"]
    if artifact.created_at > at:
        warnings.append("artifact_not_yet_created")
    if artifact.publication_state != "published":
        warnings.append(artifact.publication_state)
    if any(r.reviewed_at > at for r in reviews):
        warnings.append("future_review_not_applied")
    if review:
        state = "current_declared_review"
        warnings.append("reviewer_identity_not_verified")
        if review.outcome == "changes_requested":
            state = "changes_requested"
        if review.review_due_at <= at:
            warnings.append("review_expired")
            if state != "changes_requested":
                state = "expired_declared_review"
    if any(c.kind == "missing_information" for c in artifact.claims):
        warnings.append("known_information_gaps")
    return CatalogInspection(artifact, state, tuple(warnings))


def content_matches(artifact: CatalogArtifact, content: bytes) -> bool:
    """Verify caller-supplied bytes only; never retrieve or execute referenced data."""
    if not isinstance(content, bytes) or len(content) > MAX_CONTENT_BYTES:
        raise CatalogValidationError("Content must be bytes within the size limit")
    try:
        artifact = CatalogArtifact.model_validate(artifact)
    except ValidationError:
        raise CatalogValidationError("Artifact metadata failed validation") from None
    return hashlib.sha256(content).hexdigest() == artifact.content_sha256
