"""MemoryEntry — persistent memory is a governed clinical artifact.

Raw PHI never enters the store: clinical content is tokenized (HMAC-SHA256)
upstream in the data-boundary layer. See docs/memory-governance.md.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import FlorenceModel, utcnow
from .enums import MemoryClass


class MemoryEntry(FlorenceModel):
    entry_id: str
    memory_class: MemoryClass
    owner_role: str
    business_purpose: str
    provenance: str = Field(..., description="Where this memory came from + how it was produced.")
    content_token: str = Field(..., description="Tokenized/redacted content. Never raw PHI.")
    phi_tokenized: bool = True
    expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    last_read_at: datetime | None = None
