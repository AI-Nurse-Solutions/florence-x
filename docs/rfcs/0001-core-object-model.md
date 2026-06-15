# RFC 0001 — Core Object Model

- **Status:** Accepted
- **Date:** 2026-06-15
- **Deciders:** Technical + clinical stewards

> This RFC is also the **template**. Copy it for new decisions: Status, Date,
> Deciders, Context, Decision, Consequences, Alternatives.

## Context
Florence-X needs one canonical, validated object model shared by the orchestration
plane, the governance plane (EDENA), and the evidence layer — without circular
package dependencies.

## Decision
- All contract types are Pydantic v2 models in `packages/florence-core/florence_core/schemas/`.
- `CandidateAction` and `EDENADecision` live in **florence-core** (not florence-edena)
  so `EvidenceBundle` (core) and the EDENA client (edena) both depend *downward* on
  core. `florence-edena` re-exports them for ergonomics.
- `model_config = extra="forbid"` everywhere — no silent field drops in an auditable system.
- Enums in `schemas/enums.py` are the shared vocabulary; changing a member is
  API-breaking and requires a new RFC.

## Consequences
- Single source of truth; JSON Schemas in `schemas/` are generated from the models.
- No circular imports. EDENA stays logically separate while sharing types.

## Alternatives considered
- Defining `EDENADecision` in `florence-edena`: rejected (creates a core→edena cycle
  via `EvidenceBundle`).
