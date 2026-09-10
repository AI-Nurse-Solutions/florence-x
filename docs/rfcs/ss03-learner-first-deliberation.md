# SS-03 — Learner-first deliberation (draft)

Status before implementation: described; acceptance criteria specified first.
Baseline: SS-02 / 2761e1dff2250a862d1e3ec37efe31bf05ea1416.

## Human need and inherited commitments

The nurse needs to form an interpretation, examine alternatives and uncertainty,
and accept, revise, reject or withhold a learning conclusion without granting an
agent permission to act. Primary pillar: Judgment. Knowledge supplies the fixed
SS-02 evidence pack; Capability supplies bounded interaction and interruption;
Contribution supplies attributable, inspectable records. Poor design could turn
reflection into bureaucracy, produce anchoring, or mistake a form for competence.

Source baseline: IoC Treatise 0.1.0 (draft), Judgment section and system coupling;
Designing the Operating Environment 0.1.0 (draft), chapters 8–11 and 23. These
inherit contestability, initial interpretation before a proposal, never-preselected
verdicts and separate private reflection. They are not ratified operational policy.
The alternate IoC draft and EDENA tier conflicts remain unresolved. No tier change,
clinical authorization or assessment-validity claim is introduced. Private source
text is not included in this public engineering change.

## Proposed minimal implementation

Extend the existing companion workspace, not a new app. A versioned fixture pack
binds the unchanged mission and SS-02 evidence bytes. Three synthetic exercises
cover a missing limitation, competing findings, and persuasive unsupported certainty.
The context includes explicit synthetic observations, a prepared AI-assisted
proposal, source links and limitations. No new empirical claims or source excerpts.

Canonical Python contracts validate a bounded in-memory practice session. A pure
JavaScript reducer implements the browser interaction. Browser-generated test
records are validated against Python contracts for parity. The interface does not
call Python, a model, Hermes, a database or any external endpoint. Both contracts
are defensive programming, not authenticated identity, an audit service or a
security boundary against arbitrary same-process code or browser devtools.

Workflow: initial interpretation OR explicit uncertainty → explicit reveal →
comparison → deliberate learning choice → optional reflection. There is no default
choice. Revision requires replacement wording. All choices require a reason,
alternative and consequence; short answers are allowed and no quality score is
assigned. Reject/withhold are normal outcomes, not failures to complete.

Each round retains its context snapshot. Changing the exercise or diagnostic
evidence view invalidates the current round for further decisions. Explicitly
starting a new round preserves the previous one; returning the selector alone
does not reactivate the old decision. Previous conclusions remain historical and
are not approvals. Pause disables deliberation transitions; resume does not undo
invalidation. Twelve rounds maximum bound memory. Deliberate clear erases the
entire local practice session, with a confirmation and honest loss notice.

## Acceptance criteria (software)

1. No rendered proposal or verdict before initial interpretation/uncertainty AND
   explicit reveal. The fixture remains inspectable in source: not exam secrecy.
2. Accept/revise/reject/withhold work equally. Missing required fields, invalid
   order, extra authorization fields and unknown contexts fail without input echo.
3. A context change retains historical choices but prevents stale continuation;
   a new round binds the new context and asks for another initial interpretation.
4. Wrong mission, changed fixture/evidence pins, malformed JSON, excess rounds,
   duplicate IDs and copied invalid models are rejected.
5. Only text rendering for user and proposal content; no storage, telemetry, fetch,
   submit, upload, download or agent execution. Reload clears practice data.
6. Keyboard interaction, focus handling, pause, narrow-screen reflow and ordinary
   no-network behavior are exercised with the actual browser view.
7. Existing tests, mission/evidence records, policies, held files and original CI
   checks stay intact. New source lint and generated snapshot must pass.

## Human acceptance (not satisfied by software tests)

A nurse can state an interpretation/uncertainty, locate relevant evidence, identify
an omission or tension, explain an alternative, refuse or revise an unreliable
proposal, and explain that the recorded choice neither persists nor authorizes
execution. Observe burden and accessibility, not just preference. No participants,
results, competence score, clinical validation or reduced-overreliance effect are
inferred from this implementation. Reflection is self-guided, not a facilitated
standards-conformant debrief.

## Delivery boundaries

No patient stories, employer files, credentials, model spend, operational writes,
public hosting, policy changes, merge or release. Issue #16 stays open; seven held
files remain untouched. The immutable canonical goal record stays goal_identified;
the practice sidecar records UI learning events, not completed professional work.
Independent review, nurse evaluation, live runtime, durable record ownership,
source currency and WCAG conformance remain separate work.
