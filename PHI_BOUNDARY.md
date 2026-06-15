# PHI Boundary

**PHI stays local by default.** This is the core data-governance rule.

## Classification (`DataClass`)
`public` · `internal` · `phi_local` · `phi_redacted` · `restricted`

- `phi_local` — PHI present; must stay inside the perimeter.
- `phi_redacted` — de-identified/tokenized projection; cloud-eligible with policy approval.
- `restricted` — secrets/credentials; never persisted, never used in an action (hard block).

## Rules
1. Models work on **metadata first**: SNOMED/ICD-10 codes, aggregates, task-scoped
   summaries — not raw notes — whenever possible.
2. **Tokenize before storage**: HMAC-SHA256. Raw PHI never enters memory or audit logs.
3. **Hashes/refs, not content**: `CandidateAction` carries `proposed_payload_hash`;
   `ContextBundle` carries `content_hash` + `source_refs`.
4. **Minimum necessary**: context selection records a justification.
5. **Lineage propagation**: tagging a field PHI propagates restrictions downstream.
6. **No external model call with PHI** unless redacted + policy-approved + BAA in place.

## FHIR / SMART
FHIR R4 is the core data abstraction (read-only initially). SMART on FHIR is the
EHR-facing launch pattern. CDS Hooks is a first-class signal source.

See `docs/phi-boundary-model.md` and `tests/phi_boundary/`.
