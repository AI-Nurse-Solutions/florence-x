# SS-05B — Provider-specific offline codecs

Status: proposed engineering; implemented for testing, not independently reviewed or authorized. Baseline SS-05A `0ff906b41a2614da0ea1fb4b46bf5b073f2489cf`. Primary pillar: Capability; dependencies: Knowledge (source identity), Judgment (challenge/withhold), Contribution (inspectable provenance). Risk: mistaking schema compatibility for model quality or deployment authority.

## Scope and sources

Implement only a non-streaming, text + JSON-schema subset of Ollama `/api/chat` and OpenAI `/v1/chat/completions`. These are explicit protocol examples, not chosen paid services. The source register at `examples/provider_codecs/interface-baseline.json` records official URLs, inspection date, an immutable Ollama source revision and an OpenAI SDK type blob. Webpage byte downloads failed; no fabricated full-page hashes are claimed. Docs and source are reference-only; no vendor SDK/code/weights are bundled. Existing public excerpt rights/attribution remain unchanged. Actual model/provider terms, retention, deployment permissions and model licenses remain separate.

Official Ollama documentation says its Cloud does not support structured outputs; no cloud-Ollama compatibility is asserted. Chat Completions is not the Responses API or a universal OpenAI-compatible endpoint. Required fields/features vary by model. No selected model or installed server was assessed. `store=false` is a request parameter, not a zero-retention guarantee.

## Minimal implementation

Add provider-codec records beside, not in place of, `InferenceRequest` and `ReviewProposal`. The existing model-router package houses pure prepare/decode functions. The canonical request/mission/spec hashes remain outside the provider messages. Messages contain only a fixed system instruction/schema and the supplied task and selected passage IDs/text/version/hash. No private memory, owner identity, reflection, conversation history, credential or URL configuration is read. These input labels are not a privacy classifier or prompt-injection solution.

The new codec does not perform routing or IO, accept a user callback, or supply any execution token. It does not reuse OfflineAdmission as if it were EDENA authorization. The previous routing/admission/replay path and its tests remain unchanged. Pure serialization of already provided data is not permission to transmit it. A later executor must validate identity, context, reviewed model/codec versions, permitted endpoint and policy obligations immediately before any send.

Preparation fixes the relative endpoint and the assessed fields; unknown features cannot silently downgrade. OpenAI uses `max_completion_tokens`, one choice, `stream=false`, `store=false`, and strict JSON schema; Ollama uses `format`, `stream=false`, and `options.num_predict`. The code requests neither tools nor multimodal content. Token limits are request values, not proof of live enforcement or a global spending cap. Byte limits are not a substitute for tokenizer/context admission.

Decoding binds the exact request, specification and prepared body. Success requires the expected model name, one complete assistant text response, well-formed bounded JSON, canonical ReviewProposal validation, unique admitted passage IDs and output limits. A model alias requires an explicitly supplied expected response name; this is tested metadata, not authenticated model identity. Unknown fields are rejected except named diagnostics explicitly recorded as discarded. Refusal text, thinking text and raw errors are not emitted. No hidden reasoning is requested or treated as an audit record.

Statuses distinguish proposal_ready, refused, incomplete, unsupported_response, invalid_response, provider_error and budget_exceeded. Every non-success stops without fallback. Missing usage remains unknown, not zero. Ollama's assessed interface has no universal refusal flag; prose outside the schema is an invalid_response, not guessed into a refusal. Unknown finish states and multiple choices stop. A content-valid but false claim remains not_verified and needs human review.

## Evaluation and limitations

Use authored response fixtures (not captured outputs), independently inspect serialized field shapes, test malformed/duplicate/oversized inputs, mismatch/replay, unsupported tool/multimodal payloads, incomplete/refusal outcomes, source/authority escalation, missing counts, and no socket access. The demo reuses three existing learning questions and their admitted source context; equal proposals are expected by construction. Actual timeouts, cancellation, cumulative budgets, authenticated admission, model quality, latency and human review cost remain untested.

Acceptance was recorded before implementation. Results belong in the work report/CI artifacts, not inferred from this RFC. Preserve earlier test identities and held files; add blocking codec/report tests to the existing branch workflow. Keep original CI/lint gates. No clinical/institutional boundary, policy tier, live provider, Hermes activation, portfolio write, merge or deployment changes.

## Next gate

SS-05B can be tested within offline subset scope; overall live model substitution remains blocked until an approved endpoint/model, budget, transport controls and real comparison exist. SS-04 native-host gate remains open. SS-06 contract/failure-test preparation is independently eligible, but operational portfolio writes still require G-01/G-02. Do not convert either blocked task into a completed build count.
