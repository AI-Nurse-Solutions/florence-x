# Zero Trust Model

Every agent, API, and data flow is untrusted until verified — regardless of source.

## Controls
- **Identity-first**: verify agent identity, user role, PHI classification, action scope.
- **Deny-by-default**: network segmentation; tools expose only allow-listed actions.
- **Phishing-resistant auth**: OIDC / workload identity / mTLS (prod). The MVP
  middleware checks `X-Florence-Identity` + `X-Florence-Role` and denies otherwise.
- **Policy-as-code**: access decisions expressed contextually (OPA/Cedar).
- **High-value assets**: treat models, APIs, and pipelines with strict identity,
  segmentation, and logging.

MVP implementation: `apps/api/app/middleware/zero_trust.py`. Public probe paths
(`/healthz`, `/docs`, `/openapi.json`) are explicitly allow-listed.
