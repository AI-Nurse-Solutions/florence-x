# Clinical Safety

Florence-X is a **governance and orchestration substrate**, not a medical device
and not a source of clinical judgment. It helps AI *draft, summarize, retrieve,
monitor, and recommend* — it does not let AI own clinical judgment or execute
high-risk actions autonomously.

## Safety posture
- **Human judgment is non-transferable.** Yellow-tier and above require a named
  human to approve before execution. The loop closes on a person, never on a tier.
- **Meaningful oversight.** The steward console must give reviewers enough context
  to *challenge* the AI: evidence, provenance, missing-data flags, uncertainty,
  EDENA rationale, blast radius, reversibility (see `docs/safety-model.md`).
- **Refusal is a success.** A blocked or denied action is a correct governance
  outcome and is recorded with rationale and a safer path.
- **Latency is a safety concern.** Point-of-care workflows target ≤ 2–3s; slower
  paths get routed around and ignored.

## Scope of the open-source release
The first release proves the architecture **safely**: synthetic FHIR data only,
**no real EHR, no real PHI**. All example bundles carry a `SYNTHETIC` tag.

## Regulatory alignment
HIPAA Security Rule, ONC HTI-1, EU AI Act (human oversight, Aug 2026), FDA PCCP.
See `docs/architecture.md` (Regulatory Compliance Alignment) and `MODEL_RISK.md`.

## Disclaimer
This software is provided for research and infrastructure development. It is not
cleared or approved by any regulator for clinical use. Deploying it in a care
setting requires institutional governance (NAIO), local validation, and a BAA for
any cloud model adapter.
