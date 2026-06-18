# Design-partner pilot kit

A pilot turns "I verified it works" into "we'd run this." It is a **time-boxed,
synthetic-data** engagement that ends with a signed decision backed by evidence —
not a vibe. This kit gives you the charter, the runnable evidence report, the
acceptance gates, and the compliance checklist.

> **No real PHI, ever.** Pilots run on synthetic FHIR. Florence-X is research /
> infrastructure software, not a medical device (see `CLINICAL_SAFETY.md`).

## Who's in the room
| Role | Owns |
|---|---|
| Technical sponsor | Stands up the stack, models the pilot workflow, runs the report |
| Clinical steward (nurse/clinician) | Walks the review cockpit; judges whether the context is enough to *challenge* the AI |
| Security / compliance reviewer | Reviews EvidenceBundles + the assurance matrix against your controls |
| Florence-X maintainer | Unblocks, reviews findings, lands fixes/tests |

## A 4-week shape (compress as you like)
- **Week 0 — Verify.** `make install && make opa-install && make eval`. Confirms
  the five governance claims on your machine ([eval.md](eval.md)). Gate: `make eval` green.
- **Week 1 — Model your workflow.** Copy an example (`examples/icu_handoff/` is the
  fullest) into your own `workflow.yaml` + `agent.yaml`; add a policy overlay in
  `policies/examples/`. Keep PHI as refs; pick the EDENA baseline tier. Gate: it
  loads and runs via the CLI.
- **Week 2 — Wire a connector (synthetic).** Point the FHIR connector at your
  synthetic bundle, or add one behind the tool gateway (every call stays a
  `CandidateAction → EDENA`). Gate: the sandbox runs your workflow.
- **Week 3 — Steward review.** Run the API + console; have the clinical steward
  approve/edit/deny real (synthetic) runs. Gate: the cockpit shows enough to
  decide; resume works.
- **Week 4 — Evidence & sign-off.** `make pilot-report` → take `pilot-report.md`
  and sample EvidenceBundles to your compliance reviewer against
  [pilot-success-criteria.md](pilot-success-criteria.md) and
  [pilot-compliance-checklist.md](pilot-compliance-checklist.md). Gate: decision.

## The evidence report
```bash
make pilot-report      # writes pilot-report.md
```
It runs the MVP workflows + a refusal scenario and scores them against default
acceptance gates — every run produces an EvidenceBundle, every action passed
EDENA, PHI stayed local, zero PHI egress, latency within the point-of-care
budget, and refusal records an Incident. Swap in your own workflow to make it
*your* report. Sample output:

```text
## Acceptance gates
| Gate | Result |
|---|---|
| Every run produces an EvidenceBundle | ✅ PASS |
| Every consequential action passed EDENA (none ungated) | ✅ PASS |
| PHI work routed to local models only | ✅ PASS |
| Zero PHI egress (citations are references, not content) | ✅ PASS |
| All runs within the 3000ms point-of-care budget | ✅ PASS |
| Refusal blocks the action and records an Incident | ✅ PASS |
```

## In / out of scope
- **In:** synthetic clinical workflows, your policy overlays, your connectors
  (read-only/sandboxed), steward review, evidence/audit review, latency.
- **Out:** real PHI, production EHR writes, real model fine-tuning, anything that
  needs a regulatory clearance Florence-X does not claim.

## Next
- Define gates: [pilot-success-criteria.md](pilot-success-criteria.md)
- Compliance review: [pilot-compliance-checklist.md](pilot-compliance-checklist.md)
- Stuck or skeptical: [CHALLENGE.md](CHALLENGE.md) · open a discussion/issue.
