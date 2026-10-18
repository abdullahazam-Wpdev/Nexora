# Phase 7 delivery: bounded coding, memory and evaluated Core research

Started from `d84d5c4`, `research/phase2-model-reliability`, on 2026-10-18 Asia/Karachi. The Phase 6 audit is in `PHASE7_INITIAL_AUDIT.md`. Earlier checkpoints, datasets, services, copy/edit/canvas chat behavior and `/research` are preserved.

## Implemented and verified

- Durable subprocess task runtime with goal/acceptance data, short public plans, dependencies, audit events, role stages, bounded retries, cancellation, restart detection and scoped approval/apply recovery.
- Registered-repository Python coding: read a selected file, stage model output, check syntax/permissions, run actual sandbox assertions, revise, show diff, verify original/candidate hashes, and apply only after owner approval.
- Five role stages sharing one model proposer. Public documentation was actually read in the end-to-end demonstration. Planner/Tester/Reviewer are deterministic, not additional heavyweight reasoning models.
- Typed project memory with provenance, namespace separation, deduplication, correction, deletion and retention. Skill discovery and two validated skills. No automatic training on chats or memory.
- Real Research mode in chat with stored source excerpts and clickable citations; basic per-document redirect/frame guards. Bounded calculator and literal citation-inclusion verifier.
- GPT-OSS-20B through the existing NVIDIA NIM adapter with explicit hosted consent and final-answer-only display; separate Whisper speech view and bounded WAV adapter. Both correctly report missing credentials/service rather than pretending generation works. See `OPENAI_NVIDIA_MODELS.md`.
- Light chat layout based on the supplied screenshot: quiet sidebar, centered readable conversation, compact model selector, rounded composer, functional Chat/Research/Code/Library/Speech views, dark toggle preserved and mobile navigation. No fake subscription, provider entitlement or voice service.
- Completion-only tool-selection training with immutable separate checkpoints, exact JSON/tool metrics and reproducibility repeat.
- The earlier approved 2.84 GB NVIDIA 4B GGUF is fully downloaded, SHA-verified and stored only. It was never loaded or selected. REA's Codex registration is switched to this project's verified wrapper; restart Codex to refresh an already-connected server.

## Verification summary

Final Python suite: **77 passed**. Ruff F checks, dependency check, frontend TypeScript and production build passed. Live public search/read/citations, real local model chat, the sandboxed coding/apply demo, incorrect approval rejection, stored citation verification, independent arithmetic and actual API-restart task persistence passed. Browser checks passed on desktop/mobile; publication screenshots use isolated fixture storage. NVIDIA hosted generation and Whisper speech remain explicitly blocked by missing configuration, not falsely counted as passing.

## Evidence and results

The live feature demo used `artifacts/phase7/acceptance-repository`, repaired an addition function, rejected the wrong approval hash, then completed the exact approved patch. It included real documentation, a real SmolLM2 proposal, real container tests and the review/apply stages. `docs/evidence/phase7/live-acceptance.json` contains public fixture evidence and source identities.

SmolLM2 passed 4/20 transparent smoke tasks but 0/20 on the harder 20-utility baseline and again after explicit profile-prompt clarification; both supplied-control sets passed 20/20. The model has not demonstrated professional coding. `PHASE7_EVALUATION.md` explains policy-rejection counts, model limitations and the separately measured prompt clarification experiment.

Two separate Core pilot designs and a repeat ran for 40 optimizer steps each, 171,328 parameters and 1,600 supervised completion tokens. The wording-held-out pilot measured masked test loss 0.5841850132 / perplexity 1.7935286876, valid tool JSON 16/16, correct tool 2/16. The first pilot observed ~340.57 MiB monitored RSS and 57°C maximum sampled CPU temperature, with ~2.85 seconds including evaluation; exact per-run metrics differ and are in the JSON evidence. The repeat reproduced loss and every checkpoint tensor. Neither pilot is promoted. Existing selected Core remains 984,192 parameters with its original model hash and freshly measured 0/16 tool selection.

These are small synthetic experiments, not a foundation-model capability breakthrough. Low masked perplexity mainly reflects repetitive JSON form and must not be compared with earlier pretraining perplexity.

## Commands and locations

```sh
scripts/ollama.sh start
scripts/start-local.sh api
# separate terminal, after a production build:
scripts/start-local.sh ui
# http://127.0.0.1:3001 ; API http://127.0.0.1:8000/docs

.venv/bin/python -m pytest -q
.venv/bin/ruff check nexora scripts tests --select F
.venv/bin/python scripts/phase7-live-acceptance.py
.venv/bin/python scripts/phase7-coding-benchmark.py --suite coding-v2
.venv/bin/python scripts/phase7-coding-benchmark.py --suite coding-v2 --label coding-v2-post-prompt
.venv/bin/python -m nexora.tool_sft --run-id phase7-tool-sft-reproduce --steps 40
export PATH="$PWD/.tools/node/bin:$PATH"
(cd frontend && npm run typecheck && npm run build)
```

Task histories/candidates: `artifacts/agent-tasks/`; fixture repositories: `artifacts/phase7/`; memory: `artifacts/project-memory.sqlite3`; Core pilots: `artifacts/tool-sft/phase7-tool-sft-*/`; unchanged selected checkpoint: `artifacts/runs/phase2-small-language/checkpoints/step-0000400/`. The supervised dataset is versioned and retained with each pilot, never mixed with private chats. Existing checkpoints need no migration because their engine/format was untouched.

## Scope that remains incomplete

The working coding slice is **one pure Python file**, not arbitrary JS/TS/PHP builds, package installs, multi-file symbol indexing, WordPress/WooCommerce/Shopify deployments or privileged troubleshooting. Those workflow templates are marked proposal-only. Memory retrieval is lexical, not a full vector RAG system. Review validates constraints/tests rather than understanding every semantic flaw. Cancellation is cooperative between bounded operations. Source quotation checks do not prove arbitrary factual claims. Skill proposals require manual activation review. There is no unrestricted self-modification or automatic model deployment.

The broad eighteen-milestone request is therefore not declared fully complete. Its first coding/planning/verification/memory/reviewer/training vertical slice is implemented with measured failure cases. Stronger model reliability, general agent benchmarks, broader sandbox profiles and account-backed speech/hosted-model verification remain subsequent work.

## Phase 8 recommendation

Use the new failure records to evaluate a stronger explicitly approved instruction/code backend on the same hidden-acceptance utilities, then improve tool-choice/argument datasets with genuinely different tasks and balanced metrics. Add multi-file edits and JS/TS builds only after their sandbox profiles and approval semantics pass adversarial tests. Expand rights-reviewed training data before scaling the independent model. Keep current weights immutable and require independent evaluation before any promotion.

## Git publication

Remote SSH is authenticated and the baseline research branch matched local HEAD. Publish only the verified research branch using a normal push; never force-push or replace `main`. Weights, private conversations, API keys, vendor environments and datasets remain ignored. Final commit and remote-head confirmation are reported after the checks and push.
