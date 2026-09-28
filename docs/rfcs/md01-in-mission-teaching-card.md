# MD-01A — In-mission teaching-card draft

Status: prototype; independent review pending; no deployment authorization. The user explicitly activated the prepared mission-delivery pivot. This increment implements MD-01's memory-only scope, not MD-03 saving or MD-04 onboarding.

## Human need and capability definition

A nurse should turn the learning choice already recorded into a source-linked teaching-card draft without re-entering the decision. Primary Capability; Knowledge supplies the selected passages and explicit uncertainty, Judgment supplies all four valid choices, Contribution supplies inspectable derivation and actual review state. Poor design could make a polished card look independently approved or extract private reflection into a shareable artifact.

Users: individual professional learners; educator/preceptor is a proposed first audience, not validated demand. Only the existing public/synthetic nonclinical exercise is admitted. Personal institutional/clinical boundaries, source-framing conflicts and EDENA tier questions are unchanged. The IoC draft and OS/Harness outline inform purpose and separation of responsibilities; they do not establish educational effectiveness or authorize clinical use. No private source text is embedded in this patch.

## Baseline and smallest coherent change

Baseline Florence-X `7cfd6ced1d3400bd14224fdefa611478031ea2f9`, tree `0223fc23c0f2a7fef0ec53715cc6708dddf98495`. The exact SS-07B page SHA-256 is `461114cd4ca3f68b2faa32591b3610985bb0b69a43625cfe067f460464b5f389`.

All existing files remain unchanged. A new builder calls the existing walkthrough builder, refuses unexpected source bytes, and composes a small pure projection, its UI, and the card panel into the same internal practice closure. The original decision engine and supporting review-note code remain byte-for-byte present. The original navigation is retained, with a separate prominent teaching-card link. Existing CSP directives remain; only content hashes change.

No second decision form or general orchestrator. The only added input fields are a short card learning objective and a fixed audience selection, explicitly instructional design rather than a new mission or permission. They can be edited without duplicating the recorded choice. Source, mission, choice, goal/audience and design revision bind the derivative. Source context is not semantic verification.

## Data and lifecycle

NAIOTeachingCard consumes the existing NAIODeliberation.check result. It projects only the current decision and selected source records. It excludes initial interpretation, reflection, SOUL and conversation history. The reason, alternative, consequence and optional replacement are deliberately included, remain untrusted, and must contain only non-sensitive invented/public text. This is not an arbitrary-text privacy classifier or hostile-browser containment mechanism.

The output is a temporary_teaching_card with template_version 0.1.0, a page-session-scoped ID, a Markdown payload compatible in kind with learning_guide, and catalog_state not_registered. It is NOT a CatalogArtifact, authenticated author record, portfolio entry, ApprovalRecord or ExecutionReceipt. It does not reuse TC-001's identity/version or imply that a changing practice result is the unchanged TC-001 v0.2 document. Canonical registration and persistent IDs require a later reviewed mapping; existing catalog validators are not loosened.

Accept preserves the learner's acceptance without endorsing it. Revise displays the learner's replacement as unreviewed. Reject/withhold display learning from the decision, not an endorsed recommendation. No prepared proposal is re-published in the card. Template instructions, goal and teach-back activity are explicitly authored design, not empirical findings.

At most 12 cards exist per page session. Goal/audience edits monotonically change the presentation revision; reverting values cannot reactivate a historical card. Case/evidence changes use the existing stale-comparison rule. Pausing stops assembly and preserves drafts; clear requires the existing confirmation, and reload loses all temporary entries. Historical drafts remain inspectable, never retroactively reviewed.

## One-page presentation and failure behavior

A 720 by 960 CSS-pixel content target represents a US Letter page with half-inch margins. A conservative character budget rejects overlong wording first; a separate inaccessible measurement plane uses the same controls and typography for actual geometry. Excess height/width stops assembly. No text or disclosure is clipped, shortened, or shrunk to force a pass. The prior card and original decision text remain available. A learner can reduce the objective or start a new comparison with more concise wording. This is a preview target, not a tested printer driver or exported PDF.

The visible card reflows on narrow screens and may be taller than a physical page there. Successful explicit assembly focuses the heading with a visible cue; the next Tab reaches source inspection. Routine refresh, pause and evidence selection do not steal focus. Full source revisions, quoted passages, applicability, inspection limits and reuse notes stay in the companion.

No file writer, clipboard, print/export/download control, storage, network, model, credential, native Hermes or publication interface is added. Browser/OS-level copying or printing by a device owner is outside this UI boundary; the prototype does not claim to prevent it. Development builds and evidence files are not portfolio writes.

## Acceptance and evaluation

Acceptance was recorded before implementation: exact source/choice linkage; four genuine outcomes; excluded private fields; text-only rendering; disclosed design and review limits; stale/history semantics; pause/clear/reload; readable one-page refusal; keyboard/reflow; unchanged prior source and tests; and no new operational permission. The new suites test pure projection, composition, and actual browser interactions. Prior journey/note-focus tests run unchanged on the derived page. Actual counts, failures and environments are reported separately.

Human participants: zero recorded. Independent educator review and actual usefulness, omissions, burden and accessibility experience remain pending. No competence or learning-effectiveness claim. G-01's held files are untouched; G-02/G-03 and operational save/host/model gates remain closed. Signed installation, real storage/recovery and hosted isolation are not implemented.

## Maintenance and next work

The small extension depends on exact build anchors, not a stable plugin ABI. Drift fails the build and requires source review. Keep definition, test evidence, human review and deployment authorization separate. Retire this candidate if its source lineage or controls cannot be maintained. The next value dependency is the rights-checked, educator-reviewed learning pack and observed use of the card, not assuming more templates establish benefit. Operational continuity remains MD-03 after its gates clear.
