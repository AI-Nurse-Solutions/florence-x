# Demo video — shot-by-shot recording script (~3:30, one take)

A record-in-one-take script for a screen-capture demo. Audience: healthcare AI /
agent developers. Goal: *"this governs AI actions, and I can verify it myself."*
Tone: calm, technical, no hype. See [DEMO.md](DEMO.md) for the narrative version.

## Before you hit record (stage off-camera)
1. Terminal: large font (≥18pt), dark theme, window wide enough that `make demo`'s
   summary block doesn't wrap. Repo cloned; `make install && make opa-install` done.
2. Pre-warm so nothing lags on camera: run `make demo` and `make pilot-report` once
   (deps cached), then clear the screen.
3. Steward console staged in a browser tab: API + worker running, console at
   `localhost:3000`, and **one paused run already in the review queue** — submit a
   sync, non-auto-approve signal so it sits at `awaiting_human`. Have the queue open.
4. A second browser tab on the docs site `…/assurance/`.
5. Commands ready to **paste** (don't type live): `make demo`,
   `pytest tests/redteam -q`, `make pilot-report`.
6. Record 1080p; one continuous take, switching Terminal ↔ Console ↔ Docs.

## Shot list

| # | ~Time | ON SCREEN (do this) | VOICEOVER (say this) |
|---|---|---|---|
| 1 | 0:00–0:20 | Title card: "Florence-X — governing AI that acts." Cut to terminal. | "Most clinical-AI demos look great until the AI stops *answering* and starts *acting* — placing an order, writing a note, messaging a patient. The hard question isn't 'can it answer?' It's 'who let it do that?' Florence-X is the layer that answers that." |
| 2 | 0:20–0:35 | Terminal cleared. Paste `make demo`, enter. Let the CloudEvents lines stream. | "Here's a governed run — an ICU handoff — start to finish, no services. Watch the event stream: this isn't a chatbot, it's a workflow moving through a gate." |
| 3 | 0:35–1:00 | Highlight the summary block: `EDENA require_human (yellow)`, `final action: draft`, `evidence bundle ev_…`. | "The agent drafted a handoff — but before anything executes, it becomes a *CandidateAction* and goes to EDENA, the governance plane. EDENA says: yellow, requires a human. Nothing ran on its own. And the run produced an EvidenceBundle — the compliance artifact, by default." |
| 4 | 1:00–1:10 | Switch to **console** → review queue (paused run, tier color-coded). | "That pause shows up here — the steward console. This is the human authority interface, not a dashboard." |
| 5 | 1:10–1:40 | Open the run → approval cockpit. Slowly mouse over: proposed action, reversibility, blast radius, EDENA rationale, source citations, the five buttons. | "And here's the rule we refuse to break: a reviewer never sees a bare 'approve' button. They see the proposed action, whether it's reversible, the blast radius, EDENA's reasoning, the source evidence — everything they need to *challenge* the AI. Then: approve, edit, escalate, deny, or stop." |
| 6 | 1:40–1:55 | Click **Approve**. Show it resolve; open the run page: completed + recorded review + evidence. | "Approve — and the run resumes from its checkpoint to completion. The evidence now records who decided, the decision, the rationale, and the sources. That's your audit trail." |
| 7 | 1:55–2:05 | (Optional, second staged run) **Deny** → show blocked + an Incidents entry. | "Deny, and it's blocked — and recorded as an Incident. In this system, refusing is a *successful* outcome, not an error." |
| 8 | 2:05–2:35 | Switch to **terminal**. Paste `pytest tests/redteam -q` → `31 passed`. | "But don't take my word that the gate holds. We ship an adversarial suite that *tries to break our own claims* — 31 attacks. Run an action without a decision. Leak PHI to a cloud model. Forge an evidence record. Take EDENA down and force an 'allow.' All repelled — including a structural proof that, in the runtime graph, the tool-execution step is literally unreachable except through the gate." |
| 9 | 2:35–2:55 | Paste `make pilot-report`. Show the acceptance-gates table, all ✅. | "And if you're evaluating it: one command runs the workflows and scores them against the gates a pilot has to pass — every action gated, zero PHI egress, refusals recorded, latency in budget. This is the report you hand your compliance team." |
| 10 | 2:55–3:15 | Switch to **docs `…/assurance/`**, scroll the invariant↔attack↔test matrix. | "Every claim maps to the attack that tests it. It's all public, and `make eval` reproduces the entire proof on your machine in a few minutes — synthetic data, no accounts." |
| 11 | 3:15–3:30 | Closing card: the doctrine line + `github.com/AI-Nurse-Solutions/florence-x` + "Try to break it: docs/CHALLENGE.md". | "Florence-X orchestrates. EDENA gates. Humans decide. Nurses steward. It's open source — and if you can break the gate, that's the bug we most want to see. Link's below." |

## Captions / lower-thirds (optional)
- Shot 3: `No action executes without an EDENA decision`
- Shot 5: `Meaningful review: blast radius · reversibility · evidence · rationale`
- Shot 8: `31 adversarial tests — every invariant attacked`
- Shot 9: `make pilot-report — the evidence your compliance team reads`

## 60-second cut (social)
Shots **1 → 2/3** (make demo + the gate) → **5** (cockpit, ~10s) → **8** (`31 passed`)
→ **11** (close). Trim VO to the key sentences. End on "Try to break it."

## One-take tips
- **Paste, don't type** commands — keeps pace, avoids typos. `make demo` and
  `make pilot-report` are sub-second after warm-up, so they're safe live.
- Fluff a line? Pause ~2s and redo the sentence — easy to trim, still "one take."
- Move the mouse slowly in the cockpit (shot 5) — it's the emotional center.
- VO is ~520 words ≈ 3.5 min at a calm ~150 wpm.
