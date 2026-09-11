# SS-06A — Truthful private-portfolio contract (no writer)

Status: proposed engineering; offline contract tests only. Baseline `89e88aa241b7fa68aacf5bed0e255c73db101862`. No independent review, deployment authorization, or operational saving.

## Human need and pillar mapping
A nurse needs to distinguish a prepared artifact, a proposed save, approval, and evidence that the intended artifact actually exists. Primary pillar Contribution; Knowledge retains sources, AI disclosure and uncertainty, Judgment separates learning choices from save approvals, Capability supplies bounded attempts and recovery obligations. Risks: false assurance from simulated receipts, burden from metadata, and practice portfolios mistaken for competence.

## Baseline findings and minimum change
The inspected current HumanReview binds action/decision references, but not all proposed portfolio fields or expiry. EvidenceBundle/ToolCallRecord track executed/output_hash, but do not themselves establish full private-portfolio read-back. The non-executable catalog already binds artifact source, owner, version, content hash and AI disclosure. Reuse CatalogArtifact; do not alter old records, policies, API, runtime, held files or tier meanings.

The new PortfolioEnvelope combines the existing artifact with mission digest, owner, workspace, inert destination reference, purpose, audience and a selected learning-decision digest. It is owner-only, unsubmitted, unreviewed and not a competence claim. No source lookup, private reflection ingestion or real nurse entry is performed. The linked learning decision is not a save approval. This prototype accepts public/synthetic catalog artifacts only; future user-owned nonclinical content requires its own admission design.

## Proposed action-chain mapping — fixtures, not rival policy authority
| Intended responsibility | This increment's deliberately non-authorizing representation |
|---|---|
| ActionIntent | SaveIntentFixture binds the full envelope, actor, create-only logical key, capability version and policy reference/version. |
| PolicyDecision | SavePolicyFixture is caller-supplied synthetic input. No EDENA call, real policy permit or risk-color mapping. |
| ApprovalRecord | SaveApprovalFixture binds exact intent and policy hashes, approver and validity. It is not authenticated or professionally credentialed. |
| ExecutionReceipt | Not issued. SaveAttemptFixture is an authored assertion that a dispatch was attempted, not an execution record from a real tool. |
| Outcome evidence | SaveReadBackFixture supplies a full envelope and content; the assessor compares them but does not read storage. |

All fixture/assessment records carry offline_contract_test and no_execution_permission. There is no live-enablement switch, store adapter, callback, credential, endpoint or retry path. Writing a development report is not writing a portfolio. A later authorized executor must collect genuine evidence from independently mediated identity, policy, approval, audit and storage boundaries.

## Behavior and acceptance
Acceptance was recorded before implementation. Full envelope changes invalidate old intent bindings. The create-only logical key includes owner, workspace, destination, artifact ID and version; changed contents at that target are conflict rather than overwrite. Current and dispatch-time policy/approval/audit checks remain separate. Expiry is half-open; revocation at dispatch blocks the historical check, whereas later revocation does not erase matching historical evidence.

Reported success without read-back stays unknown. In-flight or interrupted work cannot be automatically repeated. Full read-back metadata and exact UTF-8 bytes must match; merely echoing a hash is insufficient. Absent or unavailable reads require reconciliation and do not prove an in-flight write cannot commit later. A reported failure accompanied by matching bytes remains explicitly contradictory. Repeated evaluation has no side effects; this is NOT an atomic deduplication or exactly-once guarantee.

The output separates current_guard_failures, historical_guard_failures and evidence_state. readback_matches_fixture means only that supplied assertions are internally consistent at the tested fields. It never emits a successful receipt or execution permit. It is possible for bytes to match despite invalid approval: the result preserves both facts rather than retroactively rewriting either. Current audit loss stops future work but cannot erase prior observations.

Bounded UTF-8 parsing rejects duplicate/unknown fields, non-finite JSON, invalid controls, unsupported provenance and oversized inputs. Revalidate model instances before serialization so malformed copies cannot bypass checks or emit serialization warnings with supplied content. This uses Pydantic's documented validation behavior (official Models guide inspected September 10, 2026), not a claim that typed records authenticate actors or contain a malicious process.

## Explicit limits and separate deployment gates
No actual storage/read-back, atomic reservation, concurrent writers, crash durability, encryption, deletion, retention, signed receipts, cumulative retry budget or authorization service is implemented. Observation authenticity/freshness and revocation acquisition are supplied fixture assertions; labels and hashes do not verify privacy or identity. The validator cannot prove a future storage adapter will obey it. Actual integration requires a trusted clock, owned destination registration, revision/compare-and-swap rules, durable pre-dispatch audit, atomic idempotency reservation, safe reconciliation and failure injection across the real adapter.

Issue #16's seven files stay untouched. No institutional/clinical route, PHI, employer documents, private memory, model inference, native Hermes activation, merge or deployment. Keep SS-06 operational saving blocked by G-01/G-02. Source/approval/ontology conflicts remain for authorized resolution, not synthetic policy reinterpretation.

## Evaluation and next step
Contract suite covers binding changes, actor mismatch, missing/expired/rejected/revoked approvals, unavailable audit, contradictory/partial outcomes, duplicate/conflicting targets, exact metadata/byte checks and prohibited IO. A fourteen-scenario static report is inspectable without any save UI. Runtime and nurse-understanding evaluation remain pending; tests are not evidence of educational benefit.

Next independent work is the SS-07 integrated walkthrough and formative evaluation kit, explicitly displaying blocked live model/native/save stages. Operational portfolio implementation remains gated, not marked complete merely to advance the sprint.
