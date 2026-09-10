# SS-04A — Hermes-first presentation boundary

Status: proposed engineering; prototype only. Native installation and runtime activation are not authorized.
Date: September 10, 2026. Parent: SS-03 at `5b76fa7ff2357ceff398be7cd9fa0cd2c27a4316`.

## Human need
A nurse should retain the same source-linked learning and deliberation mission when its host changes. The preferred desktop host must not silently receive the learner's private entries or acquire permission to act. Primary pillar: Capability. Knowledge supplies the admitted public evidence; Judgment preserves the learner-first workbench; Contribution preserves artifact identities and reviewable changes. Poor design could confuse access with competence, or a plugin with a security boundary.

Inherited commitments: stable responsibilities around replaceable technology; personal/nonclinical scope; separate meanings, policy, enforcement and orchestration; no inference of authority from risk colors or source metadata. These are design commitments, not evidence of deployment safety. No tier conflicts are reconciled by this patch.

## Exact upstream baseline
The GitHub latest-release endpoint returned Hermes Agent **v0.21.1**, tag **v2026.9.7**, published September 7, 2026. The annotated tag object `9949d0d324a3a06ac238e01dd1c2103dbca09900` resolves to commit `2237be355906fbe6065ce1815711eee52b2d646e`. GitHub reports the tag unsigned. This pin establishes the inspected source identity, not an authenticated installed desktop binary. Earlier chat revisions are not adopted as the deployment baseline.

`integrations/hermes-desktop/assessment.json` records inspected paths, blob hashes where obtained, scope, rights, unknowns and activation gates. This was selective static inspection, not an audit of the entire repository, packaged app, dependencies or upstream vulnerability history.

## Interface findings and decision

| Surface | Inspected evidence | Disposition |
| --- | --- | --- |
| Native desktop `HermesPlugin` / `ctx.register` | `apps/desktop/src/contrib/plugin.ts` and `types.ts`; SDK guide's disk-plugin example | **Optional plugin candidate**: one presentation pane; disabled by default. |
| Desktop runtime loader | `apps/desktop/src/contrib/runtime-loader.ts`, lines 1–125 | Loaded ESM has full renderer authority. Error isolation and hash verification are not sandboxing. Review the exact adapter bytes before loading. |
| Agent API | `website/docs/user-guide/features/api-server.md`, lines 1–170 | Guide describes full toolset handling and already-executed tool outputs. **Defer** agent traffic: output inspection is too late to authorize those effects. Server implementation and complete mediation are not verified here. |
| Native desktop vs browser dashboard plugins | `website/docs/developer-guide/desktop-plugin-sdk.md`, lines 1–130 | Different contracts and directories; do not assume one plugin works in both. |
| Desktop entry page | `apps/desktop/index.html` | Does not establish packaged Electron response-header policy; native CSP compatibility remains an explicit test. |

The SDK guide says no core plugins ship, while the pinned tree includes plugin directories. Preserve this documentation/code discrepancy; do not infer lifecycle behavior from that statement. The actual `HermesPlugin` type supports `defaultEnabled: false` and a registration callback. No current native installation or runtime endpoint was supplied or discovered.

## Smallest proposed adapter
Keep the existing standalone SS-03 workbench unchanged. A build utility validates its exact source pin and embeds those bytes into a review-only desktop plugin. The plugin imports only `react/jsx-runtime`, registers one pane and uses no `host`, RPC, REST, socket, OS, storage, model, memory, skill or clipboard interface. There is no application API, server process, credential, installer, synchronization or background job.

The frame uses `srcDoc`, an opaque origin, `sandbox="allow-scripts allow-forms"`, no-referrer and denied camera/microphone/geolocation/clipboard features. Existing child CSP retains `connect-src 'none'` and `form-action 'none'`. Internal form events are needed by the existing learner workbench; this does NOT permit form transmission under the CSP. No `allow-same-origin`, top navigation, popup or download permission is added.

Important: these controls cover the fixed child page in the tested browser arrangement, not its privileged parent, the whole Hermes app, or a compromised OS. No parent message handler is registered. A hostile host can alter its own plugin or frame. The user's practice text is memory-only and is not transferred into Hermes sessions. Host unmount/reload can discard it; no durable professional record is claimed.

The source pin, generated-file hashes and `defaultEnabled` flag do not authenticate a host, review content, or authorize installation. The plugin's top-level evaluation still occurs under the upstream loader; our top-level code only decodes fixed public bytes. Loading unreviewed arbitrary plugins remains out of scope.

## Acceptance and actual evidence
Before implementation: preserve the canonical mission bytes, disallow host API access in contract tests, retain the initial-interpretation/reveal/choice flow, and test child-origin isolation plus prohibited network/form navigation. Native-host testing and live tool mediation require separate evidence.

Observed local results: 32 new packaging/refusal cases and all 293 prior selected catalog/mission/evidence/deliberation cases passed (325 selected tests total). Twelve Node checks using an explicitly synthetic JSX/registration host passed. No actual Hermes process or React/Electron host ran.

The browser verifier is **incomplete/failing**, not passed. Initial frame permissions prevented form events; allowing internal forms while retaining the CSP restored the learning flow. The next test corrected a fieldset-level disabled-state assertion to inspect the actual textarea. On the final bounded attempt, the verifier printed nine completed checks, then errored with an execution-context reset after a synthetic form-navigation probe. That does not establish a security breach or a clean isolation result. Preserve the failing verifier and logs; investigate settlement/navigation before claiming a pass. Two local repair/retest cycles were consumed; no further changes to that test or implementation are included in this slice.

Full repository/remote results, when run, belong in the work report and do not replace the incomplete browser/native checks. Existing issue #16 remains a separate release hold. No skipped browser test is presented as passed.

## Keep / disable / replace / wrap / test / maintain
Keep: canonical workspace, evidence and decision semantics; current standalone fallback. Disable: this plugin by default; all runtime/credential/sync paths. Replace: no upstream code or professional authority. Wrap: only presentation. Test: exact bytes, registration shape, no host API usage, explicit memory limits, frame isolation, native loading and teardown. Maintain: pin and re-review on upstream, workspace, loader or CSP changes; rebuild rather than silently follow latest.

Code rights: upstream LICENSE declares MIT. No upstream runtime, binary, fonts or model weights are bundled. New adapter source follows this repository's license. Dependency/model/provider and data rights remain separate; existing short-excerpt attributions and reuse notes are retained. No private project files or learner entries are published.

## Remaining gates and next slice
SS-04 stays **in progress / prototyped**. First resolve the incomplete browser form-navigation verifier within a new bounded step. Then perform a reviewed native-host smoke test at an observed installation, including parent CSP, unload/reload and proof of no host-session access. Do not widen host policy to make it load. Use the unchanged standalone workspace when native support is unavailable.

A subsequent runtime adapter needs independently enforced admission BEFORE transmission, scoped model/tool permissions, cancellation and recovery, authenticated identity, external-action receipts and budgets. A presentation plugin is not that adapter. No clinical or institutional data path, merge, deployment or paid service is authorized here.
