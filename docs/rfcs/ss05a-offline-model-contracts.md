# SS-05A — Model-agnostic contracts, offline first

Status: proposed engineering, implemented for review; no live model integration or deployment authorization.
Date: September 10, 2026. Parent: SS-04B `99091417438b30d56ac93b5c9d9b5488238b8c00`.

## Human need and pillar mapping

The nurse's learning mission, source context and ability to contest a proposal must survive a change in model interface. A failure must not move private work to another destination without new authorization.

Primary pillar: Capability. Knowledge supplies pinned passages and distinctions between source integrity and semantic support. Judgment retains human review, explicit model choice and the option to stop. Contribution preserves source/profile/request versions and observable failure evidence. Poor design could turn contract tests into a false claim of model quality, privacy or professional competence.

Inherited requirements: portable core records; personal/nonclinical boundary; separate policy decision and enforcement; prior retrieval/transmission authorization; no silent fallback; model and runtime adapters remain distinct. These are design commitments, not empirical results. No EDENA tiers or competing source definitions are reconciled here.

## Verified code baseline and minimal change

The existing `florence_model_router.router.ModelRouter.route` uses generic labels and an `allow_cloud` flag with a legacy clinical/redaction policy interpretation. The existing `OllamaAdapter` accepts a configurable HTTP host and does not implement this new contract. They are not evidence of personal-product safety or complete egress mediation. Their existing behavior and tests remain unchanged.

Add an optional `ModelRouter.plan_inference` entrypoint and the contract implementation in the existing model-router package; canonical records live in `florence_core.schemas.inference`. The API/orchestrator is not rewired. No new runtime, dynamic plugins, model SDK, provider credentials or HTTP transport is added. The older cloud flag does not supply admission to the new path. The legacy clinical path must be separately assessed before personal product deployment.

## Contract and data flow

A validated InferenceRequest identifies the mission, its digest, one learning question, exact source spans, feature requirements and bounded output. Source records reuse CatalogSource; excerpt bytes must match their declared SHA-256. The fixed example corpus is selected through the existing SS-02 admission mechanism before the file reader runs. The demo reuses the SS-03 practice questions without reading initial interpretations, private reflections, SOUL files or session history.

An **OfflineAdmission** is a test fixture with `no_deployment_authority`, not an EDENA decision, human credential, ApprovalRecord or transferable permission token. It binds the exact request and model-profile digests, simulated destinations, validity interval and test budgets. It is supplied outside the adapter. The demo's fixture-admission helper must never authorize a real call.

Selection order: admission/time/request binding → exact profile/destination → required features and capacity → fixture suitability → invented cost/latency ordering. An explicit profile request cannot silently be replaced. Replaying rechecks admission instead of accepting a previously returned plan as authority.

Two **invented** envelope adapters demonstrate normalization: one carries a JSON-encoded text field; the other carries a structured object. They are not Ollama/OpenAI/Anthropic response schemas, real models, live services or measured provider performance. Both operate in memory. Simulated placement describes an intended test scenario, never actual network movement.

Results distinguish proposal_ready, denied, refused, timed_out, cancelled, unavailable, invalid_response and budget_exceeded. Each call consumes at most one fixture response. No automatic fallback/retry exists. A valid proposal remains unverified and requires human review; source membership checks do not establish entailment. Unknown tool payloads, malformed/duplicate-key JSON, foreign source IDs and over-budget results produce no accepted proposal.

Output-token, time and cost values are declared synthetic fixture fields, **not actual timed inference or spend metering**. Real deadlines, concurrent cumulative budgets, process cancellation, tool mediation, durable audit and complete network enforcement are future work. Hash equality is integrity only, not identity, trust or authorization. Public labels are not a privacy classifier; callers with arbitrary Python authority can alter code and fixture records. Frozen model validation is not a sandbox. Results are evidence of this code path only, not an end-to-end security assurance.

## Acceptance and tests

Defined before implementation: canonical mission/source preservation across both adapters; admission refusal before response access; destination/features before cost ranking; no substitution of an explicit model; one attempt on all error outcomes; no fallback on local timeout; no private-memory input field; all outputs labeled unverified; existing tests and held files retained.

The tests include empty/malformed/oversized/duplicate-key inputs; strict numeric budgets; unexpected credentials, messages, tools or endpoints; modified context and profile; expired/future/missing/denied admission; unknown and duplicate model identities; feature/capacity failures; refusal/timeout/cancellation/unavailability; response schema, citation and budget failures; and valid-but-semantically-false fixture text that must remain unverified. A socket backstop verifies normal replay does not require networking. This is not proof against arbitrary untrusted Python.

Local first pass: 90 new tests plus four retained legacy router cases passed. Retained catalog/mission/evidence/deliberation/companion collection and these tests: 419 passed. These collections overlap. Actual remote/full-suite evidence and any failures are recorded in the sprint work report, not inferred from local counts. The local Ruff install was unavailable; lint is not claimed until verified.

The readable report is generated from three actual replayed fixture tasks and two stop probes, not hand-authored claims of model output. `python scripts/model_contract_demo.py --output /tmp/ss05-evidence` writes an explicit development-evidence folder only. No default profile, endpoint or production service is changed.

## Rights, baseline and remaining work

No upstream model code, weights or provider data are bundled. New project code follows the repository license. Existing public-source attributions/reuse notes remain in the original source pack; only its existing excerpts and synthetic questions are read. No private Project doctrine, learner notes, patient or employer-confidential data is uploaded.

Python/Pydantic implementation references: official Pydantic v2 model/serialization documentation; installed versions and actual test environments are recorded separately. Field exclusion and frozen validation are not substitutes for access control. No compatibility with untested providers is claimed.

Separate records: capability definition is this RFC plus the code contracts; evaluation evidence is the test/demo output; independent review is pending; deployment authorization is absent; live execution history is empty. Issue #16 and native/runtime/provider gates remain blocked. No merge, deployment, provider spend, clinical activity or hosted workspace is authorized.

Next independent slice: provider-specific offline request/response codecs assessed against actual pinned official interfaces, with authentication/transport/retry behavior still disabled until G-02/G-03 and review. Only a real, approved endpoint comparison can establish live model substitution; replay parity cannot. Do not silently mark full SS-05 complete based on this contract increment.
