# Compliance reviewer checklist

For a security / privacy / clinical-safety reviewer. The question isn't "is the AI
good" — it's **"can we account for what it did, and was every consequential action
authorized?"** Evidence is the `EvidenceBundle` (per run) + the assurance suite.

## 1 · Action authorization (was it allowed?)
- [ ] Every consequential action carries an `EDENADecision` with a tier and rationale.
- [ ] No action executed before its decision (structural — see
      [assurance.md](assurance.md), `test_gate_bypass`).
- [ ] Irreversible / external / restricted actions were blocked or human-gated.
- [ ] `policy_pack_version` on each decision traces to the exact rules in effect.

## 2 · Human accountability (who decided?)
- [ ] Yellow+ actions paused for a named, role-appropriate human.
- [ ] The `HumanReview` records reviewer ref, role, outcome, and (for deny/stop) a note.
- [ ] The review screen met the anti-rubber-stamp bar (`docs/safety-model.md`).

## 3 · Data boundary (did PHI stay put?)
- [ ] PHI-bearing work routed to a local model; no raw PHI in prompts to non-local
      models, memory, or audit payloads (`docs/phi-boundary-model.md`).
- [ ] Objects carry hashes/refs, not content; connector outputs are references.
- [ ] Redaction refuses (does not best-effort) when PHI would cross the boundary.

## 4 · Auditability (can we reconstruct it?)
- [ ] An append-only event log + EvidenceBundle exist for every run, including
      blocked/denied ones.
- [ ] Records are tamper-resistant (re-save does not mutate — `test_evidence_integrity`).
- [ ] Incidents capture refusals/containment with trigger + containment actions.

## 5 · Failure posture (what happens when it breaks?)
- [ ] EDENA fails closed — governance down never yields an allow (`test_fail_closed`).
- [ ] Refusal and containment are treated as successful outcomes, not errors.
- [ ] A run survives a restart and resumes from its checkpoint ([live-e2e.md](live-e2e.md)).

## 6 · Standards & provenance mapping (your frameworks)
Map each to your controls; pointers provided:
- OWASP Top 10 for Agentic Apps 2026 + MITRE ATLAS → `docs/threat-model.md`, `docs/assurance.md`
- HIPAA minimum-necessary / de-identification → `docs/phi-boundary-model.md`
- HTI-1 / decision-support transparency → EvidenceBundle (rationale + sources)
- EU AI Act high-risk logging/oversight → append-only events + human review + incidents
- SBOM (supply chain) → `make sbom`

## Sign-off
Reviewer: ______________________  Date: __________

- [ ] Evidence reviewed against the above. Gaps logged as issues / red-team tests.
- [ ] Outcome: ☐ acceptable for pilot scope ☐ conditional ☐ not yet — notes: __________
