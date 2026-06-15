# RFC 0002 — EDENA Decision API

- **Status:** Accepted
- **Date:** 2026-06-15

## Context
Florence-X must call a *separate* governance authority before any consequential
action, and must behave safely when that authority is unavailable.

## Decision
- Contract: `POST /edena/evaluate-action` (`CandidateAction` → `EDENADecision`),
  specified in `packages/florence-edena/edena-openapi.yaml`.
- Client extracts deterministic **risk features** in Python (not Rego) so features
  are testable and reusable across backends.
- Pluggable backends: `LocalRuleBackend` (default, pure-Python), `OpaBackend`
  (OPA/Rego), `CedarBackend` (future). Parity asserted in `tests/policy/`.
- **Fail-closed**: backend error/unreachable → deny (irreversible/external) or
  require_human (otherwise). Never allow.

## Consequences
- The MVP runs end-to-end with no OPA binary; production can switch to OPA via config.
- EDENA can later be split into its own deployment without changing the client.

## Alternatives considered
- Rego-only feature derivation: rejected (harder to test, not reusable by Cedar/ML).
