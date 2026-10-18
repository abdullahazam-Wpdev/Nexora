# Capability matrix — NEXORA vs. other platforms

Built from this project's own verified state (README, delivery/verification
reports, `tests/`) and each platform's own public documentation as of
2026-10-18 (see links in [provider-capabilities.md](provider-capabilities.md)).
No platform's private weights, internals or authenticated console was
inspected. "Documented" means the public vendor states this; it is not an
independent benchmark.

| Capability | NEXORA (this project) | ChatGPT / OpenAI API | Claude (Anthropic) | Codex / OpenAI coding | Kimi | Grok (xAI) |
| --- | --- | --- | --- | --- | --- | --- |
| Own foundation model | Yes -- NEXORA Core, independently trained, currently a small (≤~2M parameter) CPU research text-predictor; no demonstrated instruction-following | Yes, proprietary, undisclosed scale | Yes, proprietary, undisclosed scale | Built on OpenAI models | Yes, proprietary | Yes, proprietary |
| Reliable instruction following / chat assistant | **No** -- explicitly not claimed; SmolLM2 135M (external reference) and Core both fail basic instruction probes per `docs/model-evaluation-report.md` | Documented, mature | Documented, mature | Documented, mature | Documented | Documented |
| Tool/function calling | Hosted-provider passthrough only (NVIDIA NIM adapter accepts `tools`/`tool_choice`, untested live); Core/SmolLM2 do not reliably tool-call | Documented | Documented | Documented | Documented | Documented |
| Local, offline inference | Yes -- Core, Ollama/SmolLM2, LocalAI all run fully local and offline on this laptop | No (hosted) | No (hosted) | No (hosted) | No (hosted) | No (hosted) |
| Streaming generation | Yes for NVIDIA NIM adapter (SSE, untested live); local providers return bounded non-streaming replies today | Documented | Documented | Documented | Documented | Documented |
| Multi-step autonomous coding agent | **No** -- cowork actions are explicit, user-directed (`/write`, `/run`, `/read`); no autonomous multi-file planning | Documented (via Codex/agents) | Documented (Claude Code) | Documented | Partial, documented | Partial, documented |
| Sandboxed code execution | Yes -- rootless Podman, no network, read-only root, dropped capabilities, 10s/96MiB bound | Varies by product | Varies by product | Documented sandboxing | Not verified here | Not verified here |
| Vision / multimodal | No (not implemented) | Documented | Documented | N/A | Documented | Documented |
| Embeddings | Via NVIDIA NIM adapter only (untested live) | Documented | Not a primary Anthropic product | N/A | Documented | Not primary |
| Reverse-engineering / binary analysis tooling | Yes -- REA + Hopper, MIT-licensed, installed and reviewed (own/authorized artifacts only) | Not a product feature | Not a product feature | Not a product feature | Not a product feature | Not a product feature |
| Training data transparency | Yes -- every ingested source hashed, licensed, provenance-recorded in `docs/dataset-strategy.md` and `catalogs/manifest.json` | Not disclosed | Not disclosed | Not disclosed | Not disclosed | Not disclosed |
| Cost to operate today | Free (local CPU/storage only; no paid API calls made) | Paid API / subscription | Paid API / subscription | Paid subscription | Paid API / subscription | Paid API / subscription |

## Reading this table honestly

NEXORA's advantage is architectural transparency, local-first operation, and
an honestly-scoped research model -- not capability parity. On raw assistant
capability (reasoning, instruction-following, coding reliability), every
hosted platform in this table documents substantially more mature behavior
than anything NEXORA Core or the pinned local references currently
demonstrate. The goal stated in the Phase 4 prompt is to *reproduce useful
workflow patterns* (chat, file ops, tool use, research) within NEXORA's own
architecture -- not to claim equivalent model quality, and this table should
not be read or quoted as such a claim.

## Phase 5 update: measured, not assumed

`docs/AGENT_EVALUATION.md` and `docs/INSTRUCTION_TUNING.md` now back the
"instruction-following" row above with real automated scores rather than
the earlier qualitative "No": NEXORA Core scores 0/5 on instruction
following, 0/2 on structured JSON, 0/3 on tool selection against
`scripts/agent_eval.py`, and a from-scratch instruction-pilot checkpoint
trained this pass scores 0/6 on a clean, disjoint held-out probe set after
appearing to score 3/5 on a contaminated (training-adjacent) comparison --
a caught and documented example of exactly the kind of inflated result this
table warns against. Ollama/SmolLM2 135M does measurably better (2/5, 1/3,
and one genuinely correct, sandbox-executed Python function), still far
short of the hosted platforms in the table above. No score here should be
read as approaching ChatGPT, Claude, or Codex-level capability.
