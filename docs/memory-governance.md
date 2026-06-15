# Memory Governance

Persistent memory is a **governed clinical artifact**, part of the agent's security
perimeter (aligned with NIST AI RMF + OWASP Agentic Top 10).

## Classes (`MemoryClass`)

| Class | Examples | Retention | PHI risk | Write |
|---|---|---|---|---|
| `operational_context` | Active run state | Session | Medium | Automatic |
| `user_preference` | Format preferences | Configurable | Low | Automatic |
| `clinical_summary` | Encounter context | Governed period | High | Human approval |
| `policy_cache` | Retrieved policy summaries | 24h + version check | Low | Automatic |
| `security_state` | Tokens, credentials | Never | Critical | Prohibited |

## Rules
- Every write is filtered, provenance-tagged, and tied to a business purpose.
- Reads evaluated against active user/task/classification + validity.
- Block secrets/credentials/high-risk instructions by default.
- Log every write/read/overwrite with provenance.
- Tokenize (HMAC-SHA256) before storage — raw PHI never enters the store.
- Per-class retention; explicit reset/deletion/rehydration controls.

Modeled by `MemoryEntry`; broker lives in `florence-core/memory` (Phase 2).
