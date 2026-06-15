# RFC 0005 — Memory Governance

- **Status:** Accepted (model now; broker in Phase 2)
- **Date:** 2026-06-15

## Context
Persistent memory is an attack surface (ASI06) and a PHI risk.

## Decision
- `MemoryEntry` requires `memory_class`, `business_purpose`, `provenance`, an
  expiry, and a tokenized `content_token`. Raw PHI never enters the store.
- Per-class retention + write rules (see `docs/memory-governance.md`).
- `security_state` (secrets) is prohibited from persistence.

## Consequences
- Memory is auditable, expirable, and PHI-safe by construction.
