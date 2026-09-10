# SS-04B — Complete the companion boundary verifier

Status: proposed change; presentation candidate only; native review/activation blocked.
Primary pillar: Capability. Dependencies: Knowledge (fixed evidence), Judgment
(learner-first flow), Contribution (observed outcomes and versioned failure record).
Human need: keep a learning workflow inspectable when the host changes, and avoid
calling a blocked, destroyed page a successful outcome. Principal risk: a passing
browser probe mistaken for native-host safety or durable recovery.

Minimal scope: repair the incomplete verifier and two lint aliases. Preserve all
plugin permissions, the pinned upstream, child workspace, and held files. No agent,
credentials, new live service, policy change, installer, merge or deployment.

## Follow-up — settled navigation and truthful recovery (September 10, 2026)

The original failure was reproduced without changing permissions. In local Chromium
144.0.7559.96, the synthetic form probe logged form-action and frame-src policy
denials, created no Playwright request, and committed the child frame to
`chrome-error://chromewebdata/`. The old verifier then evaluated the discarded
execution context. A separate top-navigation probe in the live child raised
SecurityError and left the parent intact. The error was not evidence of data
transmission, but the lost workbench document is a real availability limitation.

The repaired verifier checks live-frame controls before this destructive probe,
waits for its navigation commit and load event, requires the local error URL plus
policy-denial evidence, and asserts zero observed requests after settlement. It
then explicitly reloads the fixed preview and verifies restored mission identity
and cleared unsaved practice. There is no ignored navigation exception, implicit
retry, arbitrary sleep, sandbox/CSP relaxation, or success claim for lost work.
The test backstop aborts attempted requests but counts them first: any attempt
fails the no-request assertion. The full test report is saved even on failure.

Fourteen local browser checks passed on the first repaired candidate. They test
this Chromium/preview configuration, not every browser or native Electron.
The two new lint aliases change from re.S to re.DOTALL with no semantic change.
Generated plugin and preview bytes are unchanged. The dedicated CI now runs the
browser verifier as a blocking step with pinned Playwright 1.57.0; inspect actual
run evidence rather than inferring a remote pass from local results.

Reference: W3C CSP Level 3, form-action pre-navigation check,
https://www.w3.org/TR/CSP/#directive-form-action (inspected September 10, 2026),
and Playwright Frame documentation,
https://playwright.dev/python/docs/api/class-frame . The observed browser error
page is local test evidence, not behavior mandated by those documents. Existing
historical failure evidence above is retained.

The native installation, parent plugin authority, independent review, and complete
runtime mediation remain unverified. No code change here provides durable recovery
of practice entries, authenticated identity, model/tool calls, or permission to
install. Use the unchanged standalone workbench while the native gate is open.
