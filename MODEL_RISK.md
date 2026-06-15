# Model Risk

Florence-X is model-agnostic. Model selection is a *recorded decision*
(`ModelRoute`) governed by PHI status, risk tier, latency, and cost.

## Routing rules
| Condition | Route | PHI handling |
|---|---|---|
| Low-risk, public task | Cloud model allowed | No PHI in prompt |
| PHI-containing clinical context | Local model default | PHI stays local |
| High-risk clinical output | Local draft + EDENA + named human | Local only |
| Complex non-PHI research | Premium external allowed | De-identified inputs |
| Tool execution request | Pre-execution EDENA gate | Per-action classification |

## Local adapters (priority for clinical deployment)
Ollama (simplest), llama.cpp (portability), vLLM (multi-user throughput).

## Cloud adapters
OpenAI, Anthropic, Google, enterprise endpoints — **require a BAA, a redaction
layer, and explicit policy configuration** before any PHI-adjacent use.

## Controls
- `phi_rule: never_external_with_phi` is enforced per agent.
- Redaction pipeline runs before any external call (`florence-model-router/redaction`).
- Hallucination/clinical-sensitivity surfaced via evaluation rubrics (`EvaluationRun`).
- FDA PCCP-style change control: model/route changes are versioned in `PolicyPack`.
