# Pilot success criteria

Agree these **before** the pilot starts — a pilot with criteria written at the end
is a demo, not an evaluation. Fill `Target` together; `make pilot-report` measures
most of the governance rows automatically.

## Governance gates (must-pass — measured by `make pilot-report`)
| # | Criterion | Target | Measured | Pass? |
|---|---|---|---|---|
| G1 | Consequential actions passing EDENA | 100% | | |
| G2 | Runs producing an EvidenceBundle | 100% | | |
| G3 | PHI egress to non-local models / payloads | 0 | | |
| G4 | PHI-bearing work routed to a local model | 100% | | |
| G5 | Point-of-care latency (end-to-end) | ≤ 2–3 s | | |
| G6 | Refusals (deny/stop/contain) that record an Incident | 100% | | |
| G7 | Tools executed that were not registered (deny-by-default) | 0 | | |

## Stewardship gates (judged by the clinical steward)
| # | Criterion | Target | Notes |
|---|---|---|---|
| S1 | Review screen shows the anti-rubber-stamp context (proposed action, sources, blast radius, reversibility, EDENA rationale) | Yes | docs/safety-model.md checklist |
| S2 | Steward can Approve / Edit / Escalate / Deny / Stop and the run reflects it | Yes | |
| S3 | A paused run resumes to completion after approval | Yes | |
| S4 | Time for a steward to reach a confident decision | ≤ your target | qualitative + timed |

## Fit gates (your context)
| # | Criterion | Target | Notes |
|---|---|---|---|
| F1 | At least one of your real workflows modeled + run on synthetic data | Yes | your `workflow.yaml`/`agent.yaml` |
| F2 | At least one tool wired behind the gateway (synthetic) | Yes | |
| F3 | EvidenceBundle satisfies your compliance reviewer | Yes | [pilot-compliance-checklist.md](pilot-compliance-checklist.md) |
| F4 | Integration effort vs. your alternative | acceptable | engineering judgment |

## Decision
- [ ] **Adopt / expand** — gates met; proceed to a deeper integration.
- [ ] **Conditional** — adopt pending specific fixes (list them; ideally as
      `tests/redteam/` cases or issues).
- [ ] **No** — record why; the most useful "no" comes with a failing test.

Reviewer: ______________________  Date: __________  Outcome: ______________
