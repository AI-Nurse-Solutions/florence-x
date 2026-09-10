# Draft RFC H-003 — Read-only, non-executable artifact catalog

- Status: proposed; implementation for review, not deployment authorization.
- Date: 2026-09-09
- Baseline: Florence-X `7cb94142857d5274e1482ef8d0c6a8ebb93eeeef`.
- Deciders: human project maintainers; decision pending.
- Dependencies: PR #15 and unresolved issue #16 remain release gates.

## Human need

A nurse selecting a learning resource should be able to inspect its purpose,
intended audience, sources and versions, AI assistance, known gaps and declared
content-review history without confusing any of those with permission to act.
This is a prerequisite to the public-source professional learning mission.

Primary pillar: Contribution (attributable, inspectable resource inheritance).
Knowledge depends on preserving source snapshots and typed claims. Judgment
requires visible gaps and honest review status. Capability supplies bounded
inspection, not tool execution. Poor design could create false confidence in a
hash, a reference or a self-reported reviewer; it could also burden contributors
with metadata. Evaluation measures these risks rather than artifact volume.

## Source and code findings

RFC 0001 locates shared models in `florence_core/schemas`. Existing
`EvidenceBundle`, `HumanReview` and runtime objects describe execution and its
review, not a non-executable learning-resource catalog. The inspected tree has
no existing catalog to extend. Its current action and policy vocabulary remains
untouched. This RFC does not change EDENA, reconcile risk tiers or map a draft
philosophical document to execution permission.

The source design calls for catalog-before-adapter sequencing, explicit source
provenance, AI disclosure, separate review evidence and private/shared separation.
This implementation is a proposed engineering derivative, not ratified doctrine
or a claim of educational effectiveness. No private source documents are copied
into this public repository.

## Decision proposed

Add `schemas/catalog.py` for the artifact, source, citation, claim, AI-disclosure,
content-review and manifest contracts. Add `florence_core/catalog.py` for pure
validation, inspection and comparison of caller-supplied artifact bytes.
No API route, CLI command, model, storage adapter or runtime binding is added.

Only already-permitted **public** metadata is accepted by this first prototype.
It reuses the canonical `DataClass.PUBLIC` value. `synthetic_fixture` is an origin
label, not a new data class or an exemption from privacy controls. Patient data,
employer-confidential material, private portfolios and institutional records
are outside scope, including material merely labeled de-identified.

Each artifact has a precise id and three-part numeric version; title, purpose,
audience and owner reference; pillar mappings; sources pinned by revision and
hash; source/passage links; AI-use disclosure; limitations; and a rights note.
Rights are declared, not legally verified. Media types are plain text or Markdown;
there is no renderer or executable content type. Markdown remains untrusted text.

Claims distinguish `retrieved_evidence`, `generated_synthesis`, `inference` and
`missing_information`. A retrieved-evidence label requires a passage link.
A generated-synthesis label requires AI disclosure. Link resolution only proves
that a reference names a source in the supplied metadata: **not that the source
is genuine, current, permitted or supports the statement**. No confidence score
or evidence grade is invented.

Reviews are separate `CatalogReview` records, not runtime `HumanReview` objects.
They bind the complete artifact-definition digest, including source snapshots,
owner, scope, version and content hash. Their statuses are reported as declared
review metadata. Reviewer identity and underlying review evidence are unverified.
The effective review is the latest dated record at an explicit timezone-aware
inspection time. Future reviews do not apply; expiry, changes requested and
withdrawal remain visible. Ambiguous simultaneous reviews are rejected.
Publication and review never grant execution, publishing or clinical authority.

Digests use deterministic sorted JSON for this contract. They are not signatures
or a general cross-language canonicalization standard. Metadata changes invalidate
old bindings. This in-memory snapshot does not enforce version uniqueness across
a persistent history; a future registry must enforce append-only versioning.

## Validation and bounded behavior

Input is caller-supplied UTF-8 JSON bytes, at most 1,000,000 bytes. Duplicate JSON
keys, non-finite constants, malformed data, unrecognized fields and over-limit
collections are rejected. Content comparison accepts up to 100,000 supplied bytes.
Models revalidate existing instances; nested collections use tuples and records
are frozen against normal assignment. This is defensive API design, not a
sandbox against arbitrary Python code in the same process.

Public parse/inspection errors do not echo the input. No raw input or validation
error is logged. There are no network, file, model or tool calls in this module.
References that look like commands or URLs are never executed or dereferenced.

## Acceptance criteria stated before testing

C01-C05: JSON round-trip; public-only/unknown-field checks; exact versions and
unique identities; resolvable passage references; consistent AI disclosures.
C06-C08: Review binding rejects changed content, sources, owner or scope;
expiry/future/withdrawal are visible; matching and corrupted content differ.
C09-C11: Limits and ambiguous JSON fail; copied instances are revalidated;
command-like strings remain inert and sanitized errors do not echo content.
C12: Preserve existing code, held files, wire contracts and all blocking CI gates.

Use `pytest tests/unit/test_catalog.py -q` for isolated contract tests. The example
fixture checks both the artifact's real bytes and its synthetic source's hash.
A separate PR-scoped verification workflow runs the full repository suite with
real dependencies and disposable service containers, the existing synthetic HTTP
probe, schema comparison and blocking whole-repository lint. Full CI is not made
green by excluding the held files; issue #16 remains visible.

## Consequences and alternatives

This gives the learning mission inspectable resource definitions without adding
an execution surface. It deliberately does not save a private artifact, fetch
sources, authenticate reviewers, verify claim support or assess nurse competence.
Classifications are declarations; actual intake and rendering will require their
own enforcement and human-factors evaluation before user content is admitted.

Rejected: reuse `HumanReview` as publication approval (different authority);
create a new risk ladder (unresolved doctrine); register a portfolio writer now
(release gate unmet); present metadata validation as authorization (false claim).

## Next gates

Keep draft. Resolve issue #16 through the permitted maintenance path and obtain
fresh full CI plus human review. Next design/validation work may add a governed
evidence workspace and learner-first deliberation against public fixtures.
Private-portfolio persistence still requires deployment identity, owner binding,
policy and approval contracts, observed persistence, duplicate handling and
failure recovery. No permissions are granted by this RFC or by passing tests.
