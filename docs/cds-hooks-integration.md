# CDS Hooks Integration

CDS Hooks (HL7) invokes decision support from inside clinician workflows — a
hook-based pattern for synchronous, workflow-triggered CDS that returns cards
(information + suggestions) directly in the EHR.

Florence-X treats CDS Hooks as a **first-class signal source**: a hook call becomes
a `Signal` with `cds_hook_context` populated (`CDSHookContext` in
`florence_core/schemas/signal.py`). This lets workflows trigger at clinical decision
points without the clinician leaving the EHR.

- Hooks of interest: `patient-view`, `order-select`, `order-sign`, `encounter-start`.
- The connector lives at `packages/florence-connectors/cds_hooks/` (Phase 4).
- Cards returned to the EHR are themselves `CandidateAction`s subject to EDENA.
