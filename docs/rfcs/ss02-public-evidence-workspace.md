# SS-02: inspectable public evidence workspace

Status: implemented for review; not authorization. Base: SS-01 at
`4aa3c379691809e1cfa6d15df5f1bc821deecfed`. Clinical execution is excluded.

## Human need and source authority
A nurse needs to distinguish what a source says from an AI interpretation and
from what is not known. The inherited IoC design commitments are source/claim
separation, understanding rather than output volume, and authorization before
retrieval. The IoC drafts remain drafts, with competing doctrine unresolved.
This RFC proposes engineering; it neither rewrites EDENA nor derives clinical
permission from a color, source label or successful test.

Primary pillar: Knowledge. Dependencies: Judgment (applicability and appraisal),
Capability (bounded corpus selection), Contribution (source versions and rights).
Risks: labels mistaken for truth; polished UI mistaken for learning; reading burden.

## Minimal change
An evidence pack is a sidecar bound to the existing mission ID AND record digest.
SS-01 MissionRecord and deployment manifests remain byte-identical. Existing
CatalogSource, CatalogClaim and CatalogCitation types supply shared meanings;
new specialized fields live in `schemas/learning_evidence.py`. This avoids a
competing catalog or a premature general-purpose retrieval service.

Three primary public excerpts are pinned at passage level. Source metadata
includes author/organization, version, locator, quote hash, inspection scope,
rights note, applicability, limitations and project reinspection reminder. Hashes
cover only UTF-8 excerpt text, not entire source pages. Certainty is explicitly
not appraised; recommendation strength is not assigned. Research, standard and
guidance have different purposes. This is not a systematic review.

`load_admitted_evidence` compares an exact requested pack/version/mission/scope
against an application-owned admission record BEFORE calling a fixed reader.
Unknown/nonpublic selections cause no reader call. Returned bytes must match the
pinned package digest. No caller path or URL is passed to a reader. It is a
build-time admission check, not authenticated multiuser access control, DLP,
EDENA deployment authorization or a sandbox against arbitrary Python.

Inspection reports missing passages, changed revisions, changed text, overdue
project review and future capture. Exact quote matching never implies semantic
truth; synthesis and inference remain linked-not-verified. A misleading linked
interpretation does NOT become verified merely because its reference resolves.

The existing companion workspace gains source/claim cards, type filters, a working
glossary, source-pack inspection, and explicitly synthetic diagnostic copies.
Diagnostic choices do not modify the original evidence, mission, or a decision.
No responses or notes are collected. No model, network reader, account, Hermes,
portfolio, publishing or institutional functionality is activated.

## Acceptance before evaluation
1. Three to five inspected public primary passages, with versions, locators and
   rights/reuse notes. No full copyrighted document or private project source upload.
2. Evidence, synthesis, inference and missing information stay distinct in UI.
3. Unresolvable references and changed pins never yield supported/approved badges.
4. Disallowed selections fail before reader invocation; tampered bytes fail closed.
5. Mission ID and record remain intact in all deployment previews and diagnostics.
6. Source text renders as text; browser interaction creates no network requests.
7. Existing tests stay; new tests and exact run conditions are recorded.
8. A nurse can locate a passage and state a limit. This human acceptance criterion
   remains pending until a real walkthrough is recorded; software tests do not satisfy it.

## Review and evaluation limits
The source author abstract for Buçinca et al. was read, not critically appraised
against the complete methods. NIST and W3C documents are guidance/standards, not
outcome evidence. Working summaries/glossary are AI-assisted, unreviewed project
material. No automatic semantic entailment or current-source surveillance exists.
The project reinspection reminder is a proposed maintenance date, not evidence
that a publication becomes invalid then. Offline preview presents the snapshot
inspection date; it is not claiming a fresh online appraisal on each opening.

The new workflow runs full tests, snapshot comparison, existing action/decision
schema comparison and existing synthetic HTTP checks, retaining blocking lint.
No existing workflow, policy, held file or test is removed. Issue #16 remains open.
Independent review, clean CI and deployment authorization remain separate gates.

Next: SS-03 learner-first deliberation, preserving this evidence bundle as its
context. Do not enable operational saving or live models as part of this RFC.
