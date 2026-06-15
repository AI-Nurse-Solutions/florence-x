# RFC 0006 — PHI Boundary

- **Status:** Accepted
- **Date:** 2026-06-15

## Context
HIPAA + EU AI Act + Zero Trust require PHI to be governed at runtime, not just at rest.

## Decision
- `DataClass` drives routing: `phi_local` never leaves the perimeter; `restricted`
  is never persisted/used in actions (hard block).
- Governance objects carry hashes/refs, never raw content
  (`CandidateAction.proposed_payload_hash`, `ContextBundle.content_hash`).
- External model calls require redaction + policy approval + BAA.
- Enforced by `tests/phi_boundary/`; runs on any context/model/memory change.

## Consequences
- PHI leaks are caught structurally and in CI, not by reviewer vigilance alone.
