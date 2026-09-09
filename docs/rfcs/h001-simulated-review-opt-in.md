# Draft RFC H-001: server-controlled simulated review

Status: proposed; implemented for review; not deployment authorization.
Baseline: `09675bf61062534e21e1e4aded2f6a14e48f6b8e`.
Scope: API/orchestrator service only. No policy-tier changes.

## Human need

A required human decision must not be silently replaced by a demonstration
reviewer merely because a caller adds `auto_approve=true` to a request.

Primary pillar: Judgment. Dependencies: Capability (boundary enforcement),
Knowledge (clear simulation disclosure), Contribution (reviewable change and tests).
Poor design could weaken oversight by presenting this narrow guard as complete
safety, or disrupt development demonstrations without a migration explanation.

## Verified source behavior

At the baseline, `apps/api/app/routes/signals.py` forwards `auto_approve` from
the request to the service. The service `_runtime_for` selects an
`AutoApproveReviewer` when it is true. The queue also carries the value.
There is no separate server opt-in in these inspected paths.

## Proposed change

`FLORENCE_ALLOW_SIMULATED_REVIEW` defaults to disabled. Only the value `true`
(case-insensitive, whitespace-trimmed) enables simulation. Unrecognized values
remain disabled. Request headers, role strings, source labels, and query
parameters cannot set this process configuration.

The API rejects an unpermitted request with HTTP 403 before obtaining the
orchestrator. Direct service submit/enqueue paths check before selecting,
persisting, or queueing work. The final runtime factory checks again before
creating the reviewer.

An older queue item is a request, not authority. A worker with simulation disabled
logs the downgrade and uses the ordinary policy-driven reviewer, preserving the
run id and original request. It does not discard the job or fabricate an approval.
This does not make every action require human review: the existing EDENA decision
still determines whether the ordinary workflow pauses.

## Migration

Normal usage omits `auto_approve` or sets it to false. Synthetic development API
and worker processes that intentionally use simulated approvals must explicitly
set `FLORENCE_ALLOW_SIMULATED_REVIEW=true` in their server environment. Restart
processes after changing settings. Never enable this for patient, institutional,
or otherwise consequential work. An isolated test may monkeypatch the setting
for that test only; do not enable it for the entire test suite.

This flag is a simulation switch, not a clinical-mode switch, credential,
deployment approval, or permission to use confidential data. No live setting is
changed by this patch.

## Acceptance and evidence

The dedicated suite checks default-deny configuration, explicit opt-in,
non-boolean programmatic values, pre-side-effect service rejection, both runtime
factory branches, handler 403/normal statuses, and queued-worker revalidation.
Existing synthetic API and WebSocket examples in tests explicitly opt in.
Two additional HTTP integration cases cover the forbidden request.

Local verification: 35 unit/handler tests passed on Python 3.13.5, pytest 9.0.2,
using the real changed config/service/handler source and explicit stand-ins for
unavailable runtime/schema/persistence dependencies. A before/after probe selected
an AutoApproveReviewer at baseline and raised SimulatedReviewDisabled after the
patch with server simulation disabled. No action was executed by that probe.

These are isolated boundary tests, not an end-to-end run. The full repository
suite, the two new HTTP integration cases, real graph/minimal execution, OPA,
Postgres, Redis, nurse testing, and deployment behavior were not verified locally.
Run the complete repository CI and resolve compatibility failures before merge.

## Scope limits and next gates

This does not harden direct library/CLI construction, authenticate human reviewers,
verify transport identity, bind approvals to plans, make simulated execution
receipts truthful, or provide data-loss prevention. These remain separate work.
A server operator can deliberately enable simulation; this guard does not defend
against a compromised host or a malicious administrator.

Do not infer that this repository revision is the currently deployed Nurse AI OS
runtime. That linkage requires a deployment inventory. No private project drafts,
SOUL content, patient data, or employer-confidential files accompany this RFC.

Next increment: independently verify the real action path, then implement one
nonclinical private-portfolio save with observed persistence, duplicate handling,
and recoverable failure. Keep publication and deployment authorization separate.
