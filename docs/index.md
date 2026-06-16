# Florence-X

**A governance-first, local-first AI orchestration control plane for high-trust
clinical environments.**

> Florence-X orchestrates. EDENA gates. Humans decide. Nurses steward.

Florence-X turns institutional signals into bounded, auditable, human-stewarded
workflows. It routes tasks to registered agents, assigns tools and memory, selects
local or external models, pauses for human review, invokes **EDENA** for action
gating, records evidence, and prevents AI systems from acting outside their
authorized scope.

## Three planes
| Plane | Role |
|---|---|
| **Florence-X** | Orchestration runtime — how work moves through agents, tools, models, humans. |
| **EDENA** | Governance authority — should an action be allowed, reviewed, constrained, escalated, blocked, stopped. |
| **NAIO** | Institutional oversight — which AI systems are approved, monitored, decommissioned. |
| **Nurse / clinician** | Stewardship — supervises governed AI labor in practice. |

## The canonical loop
```
Signal → WorkflowRun → AgentInvocation → CandidateAction
       → EDENADecision → HumanReview | SystemBlock | ToolExecution
       → EvidenceBundle → EvaluationFeedback
```
No consequential action executes until a `CandidateAction` passes EDENA. Every run
produces an `EvidenceBundle`. PHI stays local by default.

## Where to go next
- **[Install & run](install.md)** — clean-clone bootstrap, env vars, the full stack.
- **[Demo walkthrough](DEMO.md)** — the governed loop, refusal, human authority, evidence.
- **[Reference architecture](architecture.md)** — the 9-layer model.
- **[Roadmap & contributing](ROADMAP.md)** · **[RFC process](rfcs/README.md)**.

!!! warning "Not a medical device"
    Research/infrastructure software, not cleared for clinical use. The
    open-source release uses synthetic data only. See the safety model and
    `CLINICAL_SAFETY.md`.
