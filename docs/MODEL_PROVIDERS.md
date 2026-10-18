# Model providers — unified registry

Source of truth: `nexora/provider_registry.py` (machine-readable, served at
`GET /api/cowork/providers`). This is the human-readable view, re-verified
2026-10-18. Detailed evidence for each row lives in
[provider-capabilities.md](provider-capabilities.md) and
[integrations.md](integrations.md); this table exists to satisfy the unified
selector's "real metadata per provider" requirement in one place.

| Provider | Kind | Local/Hosted | Auth | Status today | Verify with |
| --- | --- | --- | --- | --- | --- |
| NEXORA Core | local | local | none (localhost) | Working; small research text-prediction model, not an instruction-tuned assistant | `GET /api/training`, `POST /api/generate` |
| Ollama / SmolLM2 135M | local | local | none (localhost) | Verified pinned external reference inference | `GET /api/reference/status` |
| LocalAI | local sidecar | local | none (localhost) | Verified CPU inference engine (not itself a model) | `scripts/localai.sh start` then chat routing |
| Free Claude Code (FCC) proxy | local sidecar | local | local bearer token (`.secrets/fcc-token`) | Verified; proxies to local Ollama only, never a remote model | `scripts/fcc.sh status`; see [FREE_CLAUDE_CODE.md](FREE_CLAUDE_CODE.md) |
| NVIDIA NIM | hosted | hosted | `NVIDIA_NIM_API_KEY` (Bearer); not required for model discovery | Model discovery **verified live** this pass (81 real models, no key needed); chat/streaming/embeddings implemented but need your own key -- see [NVIDIA_NIM.md](NVIDIA_NIM.md) | `GET /api/nvidia/status`; see [NVIDIA_NIM.md](NVIDIA_NIM.md) |
| OpenAI | hosted | hosted | `OPENAI_API_KEY` | Documentation-only reference skill; not connected | `.agents/skills/nexora-openai` |
| Anthropic | hosted | hosted | `ANTHROPIC_API_KEY` | Documentation-only reference skill; not connected (FCC is unrelated) | `.agents/skills/nexora-anthropic` |
| DeepSeek | hosted | hosted | `DEEPSEEK_API_KEY` | Documentation-only reference skill; not connected | `.agents/skills/nexora-deepseek` |
| Perplexity | hosted | hosted | `PERPLEXITY_API_KEY` | Documentation-only reference skill; not connected | `.agents/skills/nexora-perplexity` |
| Kimi | hosted | hosted | `KIMI_API_KEY` | Documentation-only reference skill; not connected | `.agents/skills/nexora-kimi` |
| xAI / Grok | hosted | hosted | `XAI_API_KEY` | Documentation-only reference skill; not connected | `.agents/skills/nexora-xai` |

## Context window and capability metadata

NEXORA does not display invented context-window or capability numbers for
hosted providers it has not connected to. `/api/nvidia/models` already
returns the real model ids from NVIDIA's public `/v1/models` catalog today,
with no key (81 ids, verified live this pass); once `NVIDIA_NIM_API_KEY` is
configured, generation/embeddings/tool-calling also work for the models that
support them. Per-model context length and modality are not included in that
catalog response and must be checked on the model's own catalog page before relying
on it.

## Selector requirement

The frontend model selector should read `/api/cowork/providers` (existing)
plus `/api/nvidia/status` for the NVIDIA row's live authentication/
availability state, rather than hardcoding any provider's capability. This
wiring is implemented at the API layer in this pass; frontend selector UI
changes to surface `/api/nvidia/*` were not made in this session -- the
existing provider list already renders from the registry, so adding the
NVIDIA row required only the registry entry above, but a dedicated "test
connection" button in the UI (Phase 4 §3) is still frontend work, not done
here. See [PHASE4_VERIFICATION.md](PHASE4_VERIFICATION.md).
