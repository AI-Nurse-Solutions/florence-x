# PHI Boundary Model

See also the top-level `../PHI_BOUNDARY.md`. **PHI stays local by default.**

## Classification → routing

| `DataClass` | Meaning | Cloud-eligible? | Memory? |
|---|---|---|---|
| `public` | Non-sensitive | Yes | Yes |
| `internal` | Org-internal, non-PHI | Yes (policy) | Yes |
| `phi_local` | PHI present | **No** (local only) | Tokenized only |
| `phi_redacted` | De-identified projection | Yes (policy + BAA) | Tokenized |
| `restricted` | Secrets/credentials | **Never** | **Never** |

## Mechanisms
- **Metadata-first**: prefer SNOMED/ICD-10 codes, aggregates, task-scoped summaries.
- **Tokenization**: HMAC-SHA256 before any storage. Raw PHI never enters memory/audit.
- **Hashes & refs, not content**: `CandidateAction.proposed_payload_hash`,
  `ContextBundle.content_hash` + `source_refs`. `Signal` references payloads by pointer.
- **Minimum necessary**: `ContextBundle.minimum_necessary_justification` is required.
- **Lineage propagation**: tagging a field PHI propagates restrictions to downstream agents.
- **Redaction before external calls**: `florence-model-router/redaction`.

## Verification
`tests/phi_boundary/` asserts governance objects carry hashes/refs and that no raw
clinical string survives into the evidence bundle. Run on any context/model/memory change.
