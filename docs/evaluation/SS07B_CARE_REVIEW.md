# SS-07B — Preserve the learner's place

## Review identity and scope

This is a development-agent review of SS-07A at `6b18d539ca78143a550cae5298b22a4e3e929f44`, not independent professional review, a nurse walkthrough, or an accessibility certification. No participants, feedback, consent or credentials are invented. Human participants remain zero; SS-07 human acceptance is pending.

Human need: a nurse using the keyboard should reach the note they explicitly assembled, rather than lose their place in a long page. Primary Capability; Knowledge supplies the existing unsaved-status description, Judgment retains the four genuine choices, Contribution carries the source-linked note. Poorly designed focus changes could interrupt reading or imply that assembly is approval.

## Observed defect

In the supplied-HTML Chromium test, keyboard activation of Assemble temporary review note disabled that button and left `document.activeElement` at `BODY`. The note heading had no tabindex. This is a reproduced interaction defect, not an observed human failure. The new regression fails on that exact assertion against the unchanged pre-repair page.

## Acceptance before repair

After explicit successful assembly for accept, revise, reject and withhold, focus must reach the visible note heading, expose its existing unsaved-status description, and have a visible focus cue. The heading must not add an ordinary Tab stop. The next Tab must reach the note's first source-inspection control. Pause/resume, evidence changes and refused assembly must not steal focus. All original journey checks and source data must remain intact; no save, model, upload or authority may be introduced.

## Smallest change

Make the heading programmatically focusable with `tabindex=-1` and associate the existing note-status text using `aria-describedby`. Transfer focus only after successful, explicit assembly; retain the existing scroll behavior. Give the heading an explicit focus outline using the existing palette. Do not move focus on every render. No note fields, choice semantics, storage, permissions or model calls change. The original SS-03 workspace, decision engine, evidence pack and Hermes pin remain unchanged.

Technical reference: W3C, Understanding WCAG 2.2 SC 2.4.3 Focus Order, inspected September 10, 2026: https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html. This guidance informs the repair; no full WCAG conformance or screen-reader behavior is certified. A screen-reader check and actual user observation remain required.

## Evidence and remaining questions

The new scripted verifier covers four choice paths, heading focus/description/outline, subsequent source navigation, no focus theft during pause or evidence change, refusal when stale, narrow-screen visibility and reload. It performs no network or store operation. Preserve the pre-repair failure alongside passing results; actual counts and environments belong in the work report and CI evidence.

Reading burden from the long page, the older canonical mission's limitation wording and facilitator workload remain hypotheses for actual review, not quantified human findings. This repair does not resolve them. Do not add more forms or contracts to simulate missing user evidence.

## Human handoff

The existing five-task SS-07 formative kit remains the evaluation protocol. The next step is review of the repaired experience and voluntary, permitted nurse observations. Ask what first becomes unclear or unnecessarily effortful, whether the learner can explain why the note is unsaved, and whether the note is useful for their stated purpose. A founder's product feedback and an independent review are separate evidence categories. Do not infer participation from opening a file.

Keep completed observation notes outside public source control under agreed access and retention arrangements. Do not collect patient stories, employer records, SOUL data or private reflections. No recruitment, messaging, recording or data collection is started by this change. No employment ranking, competence score or requirement for unpaid participation.

After this bounded repair, queue SS-07 for human review rather than manufacture another autonomous task. Keep maturity and review status separate: prototype; not independently reviewed. G-01 (held CI files), G-02 (runtime authority) and G-03 (live provider access) remain closed. No held-file edits, merge, deployment, native activation or live saving.
