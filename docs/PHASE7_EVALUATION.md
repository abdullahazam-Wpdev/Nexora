# Phase 7 evaluation

Starting baseline: 64 tests passed at `d84d5c4`. Final suite: 77 tests passed, alongside Ruff, dependency, TypeScript and production-build checks. This document distinguishes execution controls from model capability. Exact public fixture results and model responses are in `docs/evidence/phase7/`; private conversation databases, source repositories, weights and datasets are excluded from Git.

| Evaluation | Observed result | Interpretation |
|---|---:|---|
| Selected independent Core, fresh held-out tool choice | 0/16 | No demonstrated structured tool capability |
| SmolLM2 coding-v1 smoke | 4/20 | Narrow microtasks; prompt exposes required expression |
| Supplied control patches, coding-v1 | 20/20 | Sandbox/review/apply path works; not model success |
| SmolLM2 coding-v2 utility repairs, baseline | 0/20 | Strict profile rejected many generated test/import blocks; not evidence every candidate had incorrect function logic |
| Supplied control patches, coding-v2 | 20/20 | Same deterministic acceptance path passes known fixes |
| SmolLM2 coding-v2 after explicit profile prompt | 0/20 | Prompt clarification did not improve success; controls remained 20/20 |
| Completion-only Core JSON schema, wording-held-out | 0/16 → 16/16 | Output-form learning |
| Completion-only Core correct tool, wording-held-out | 0/16 → 2/16 | 12.5%, chance-level across eight classes; not useful routing |
| Repeated 40-step wording-held-out pilot | Identical loss and model tensors | Reproducibility check passed |

Coding-v2 baseline ran in 113.29 seconds, with 98 recorded tool/stage actions and 40 failed proposal attempts. Twenty candidates triggered profile-policy rejection. These are **policy-rejected attempts**, often harmless but unsupported imports/test boilerplate, not twenty malicious host actions. All were blocked before original-file changes. A post-measurement prompt clarification now tells the proposer the permitted imports and asks it to omit test/main blocks. Its separate post-change benchmark preserves the baseline rather than overwriting it; see the delivery report and corresponding evidence file for actual results.

The real demonstration reached owner approval and completed a model-generated addition repair after reading public Python documentation. A wrong approval hash was rejected. The actual Python acceptance assertions ran in Podman. A simple successful demo does not overturn the broader 0/20 utility baseline.

Research was live-reverified with a real Wikipedia search, three public page reads, source hashes, timestamps and extractive citations. The page reader now validates each document redirect/frame and blocks active subresources in its read-only profile. This remains a basic SSRF guard, not a production hardened anti-rebinding proxy. The response-verification endpoint checks literal inclusion in stored citation text; it does not claim semantic entailment for arbitrary prose. The calculator computes a bounded AST independently and never invokes eval.

NVIDIA GPT-OSS-20B chat and Whisper transcription are **configuration-blocked**, not passed live model tests. Public GPT-OSS catalog discovery passed. Local Ollama chat passed; LocalAI/FCC adapters remain preserved from prior verified milestones. Their full four-provider inference matrix was not rerun as a Phase 7 quality comparison.

UI verification covers the reference-like light desktop/mobile layout, chat tools, Code controls, memory storage, hosted consent and disabled/unconfigured Whisper state. Source-backed Research mode is wired through persisted conversations. Test fixtures and screenshots for publication use an isolated API storage directory to avoid leaking private conversation titles.

No scores here imply broad instruction following, multi-file professional coding, unrestricted multi-agent autonomy or production readiness. Negative cases and raw narrow benchmark limitations are retained.

The post-prompt experiment took 137.80 seconds and still scored 0/20, with all 20 control patches passing. This failed improvement is retained; the permission profile was not weakened to obtain better numbers.
