# Safety & Human-Oversight Model

## Two oversight modes
- **Human-in-the-loop (HITL)** — workflow pauses; a human must act before execution.
  Required for Yellow and above.
- **Human-on-the-loop (HOTL)** — AI acts; human observes and can intervene within a
  window. Valid only for Green with audit trail + alerting.

Routing is **confidence/tier-driven** — the workflow decides when a human is needed,
not the reviewer. This prevents the review queue becoming a rubber-stamp bottleneck.

## Meaningful review (anti-rubber-stamp)
The steward console MUST show, per action:
AI output + confidence · source evidence + provenance · missing-data flags ·
uncertainty · EDENA tier + rationale · what the action does · blast radius ·
reversibility · the accountable human · **Approve / Edit / Escalate / Deny / Stop**.

## Containment
`Incident` records safety/security/privacy/performance events. EDENA `contain`
restricts agent scope; `stop` halts the run and opens an incident. **A blocked
action is a successful governance event, not a failure** (`refusal is a governance event`).

## Latency
Point-of-care paths target ≤ 2–3s end-to-end (retrieval + inference + render).
Local models are the primary path for interactive clinical workflows.
