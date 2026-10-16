# Phase 3 delivery — independent foundation-model scaling

Continued `research/phase2-model-reliability` from clean commit `72ea4d7`. No dashboard redesign, unrelated agents, system-wide packages, GPU driver changes, paid APIs or purchases were made.

## Previous milestone verification

Read the required four reports and inspected actual Git state, model/trainer, dataset manifests, tokenizer/shards and checkpoints. The original 984,192-parameter model reproduced validation loss **4.403331741442086**, test loss **4.1786155273320755**, and perplexity **exp(4.1786155273320755) = 65.27541859339495** with zero numerical discrepancy before modifications. Its tensor/data hashes and source identity matched. All original **19 tests** and relevant integration checks passed. See [verification](phase-3-verification.md) and `evidence/phase3/baseline/summary.json` for commands, stdout/stderr, durations and exit codes.

## Actual dataset/model research

A version-pinned, license-reviewed PSF-2.0 expansion acquired/cached **282,239 bytes**, preserving notices/provenance/source hashes. Training documents increased **642→1,406**, text **166,170→353,802 characters**, with **18 exact duplicates removed**. Frozen validation/test contain 48/60 documents; old controlflow test is excluded from training. Independent checks found zero exact-document/source/12-word-shingle train/held-out overlap and zero within-split exact duplicates. These checks do not establish semantic independence or comprehensive privacy/legal verification.

Synthetic hardware probes measured three feasible configurations. Real matrix runs used fixed tokenizer, context 128, batch 4, accumulation 2, two seeds and common LR schedule. All six candidates have **step-128 / 131,072-token** checkpoints:

| Parameters | Mean held-out validation loss | Sample SD, 2 seeds |
| ---: | ---: | ---: |
| 172,352 | 5.270268 | 0.013380 |
| 984,192 | **5.069564** | 0.093849 |
| 2,115,264 | 5.151599 | 0.066065 |

The validation-selected checkpoint is `phase3-baseline-s43`, **step 128**. Only after freezing that selection, its new held-out test scored loss **4.87353038685053**, perplexity **130.78181324031158**, **4,639 targets**. No test ranking of all candidates was performed. Scores are not comparable with the old test perplexity because its sources/training token budget differ.

The wider model did not win at this budget. Generation diagnostics show repetition/fragments; strict instruction probes scored **0/4**. No useful assistant, reasoning or coding capability is established. The previously served Phase 2 checkpoint remains selected; no weaker/new experimental checkpoint was automatically promoted.

## Measured engine changes and performance

Expensive sensor reads were a measured bottleneck (~40 ms/check). Batched full-window evaluation and 0.25-second temperature sampling reduced original-model monitored validation **1.800→0.112 seconds**; loss rounding difference is **7.3×10⁻⁸**. Memory/disk/time/cancellation checks remain per call, with an added 15% battery reserve. No architecture tensor layout rewrite was needed. Configurable depth/width/heads/context are validated and capped for laptop use.

Warm greedy CPU inference measured ~**340 tokens/s** without loading/KV cache. Real corpus training-only rates were ~**20–22K tokens/s** (172K model), **7.0–7.2K** (984K), **4.65K** (2.12M). Corresponding training-only seconds/million tokens: **45–50**, **139–143**, **215**. Full run times include overhead and are reported separately, not presented as matched-step timings. Peak process RSS was **352/392/432 MiB**, max observed matrix CPU temperature **72°C**. Buffered checkpoint save median on the baseline was ~0.0196 seconds; real run checkpoint totals and CPU utilization are retained in raw results. Page-cache timing is not a durable storage guarantee.

The CPU scaling report extrapolates beyond the measured range with explicit uncertainty: a 10M model/200M-token illustrative workload is ~51 kernel-only hours under a linear extrapolation, not a measured promise or an approved job. No such workload was launched. GPU report compares verified manufacturer VRAM/power/PSU specifications and whole-system RAM/NVMe/cooling/UPS needs, without pretending gaming/AI TOPS equals measured training throughput or inventing retail prices.

## Budget cutoff, errors and recovery

The initial matrix controller had an undefined-variable error after completing its first run. It was corrected; that checkpoint was verified/reused, never overwritten. Probes underestimated sustained runtime. The recovered invocation hit its **240-second cap** and interrupted the final wider run. Including the failed initial invocation, overall research wall effort was longer than 240 seconds; the initial cap did not span retries. The final framework now persists a plan fingerprint/deadline across retries, with a dedicated regression test. Its original ledger is marked exhausted. The planned dataset-size ablation was **not run**, and no benefit of corpus expansion is inferred from it.

All six common step-128 checkpoints permit a fair matched-token comparison despite the interrupted longer run. The interrupted worker was recovered **128→130** solely as a short recovery check, preserving step 128. A separate owned-worker **SIGKILL** test verified interrupted status, valid prior checkpoint, **2→4-step recovery**, and unchanged original checkpoint. Final-input validation also caught and fixed acceptance of a negative battery reserve; exact pre-fix experimental source was archived with matching hashes.

Explicit v2/v3 migration forks preserve parent weights/data/optimizer/sampler/schedule and record both identities. Tests compare the actual committed v2 trainer's next update with v3, and v3 fork resumption with uninterrupted training. A real final-revision fork continued `phase3-baseline-s43` **256→257** as compatibility verification, outside the scaling matrix. This is not a claim that arbitrary future numerical code changes are automatically equivalent.

## Final tests and integrations

**29 tests passed**, including all original 19 plus batched-evaluation/RNG equivalence, source freeze/contamination protection, configurable architecture, sensor sampling/cancellation, invalid inputs, v2/v3 exact migration, version preflight, generation diagnostic semantics and persistent deadline behavior.

Final Ruff, TypeScript, production build, npm audit, pip consistency/audit and real browser QA all exited 0. Python audit still does not directly recognize the CPU-specific torch wheel; this is not a binary/security proof. Separate actual API QA verified launch/concurrent rejection, restart persistence, **6→8** resume, checkpoint verification, per-run/selected inference and cooperative cancellation. Existing PostgreSQL/Redis remain healthy localhost services; SQLite remains the application database.

Evidence: `evidence/phase3/final/summary.json`, `final-api-e2e.json`, `interruption-recovery.json`, `matrix-interruption-recovery.json`, `compatibility-fork.json`, `infra-status.json`. The only frontend modification accepts deliberately withheld `null` test metrics; no design was changed.

## Checkpoints, commands and files

Exact commands/configuration/checkpoint locations: [Phase 3 operations](phase-3-operations.md). Principal matched winner:

`artifacts/runs/phase3-baseline-s43/checkpoints/step-0000128/model.safetensors`

The original model remains at:

`artifacts/runs/phase2-small-language/checkpoints/step-0000400/model.safetensors`

Data and checkpoints stay outside Git. Source/manifest/evidence files are committed; exact experiment source snapshot and trained bundles remain locally in `artifacts/`.

Changed source: `nexora/research.py`, `jobs.py`; new `expansion.py`, `scaling_experiments.py`, `generation_eval.py`. New reviewed source catalog: `configs/phase3-data.sources.json`. New tests: `tests/test_phase3.py`. Scripts: checkpoint migration, baseline/optimized benchmark, matched comparison, report generation, real interruption recovery and final verification. Minimal null-metric guard: `frontend/app/page.tsx`. README/roadmap and Phase 3 verification/operations/scaling/GPU decision reports updated; detailed evidence lives in `docs/evidence/phase3/`. No new dependencies were installed.

## Limits and next research milestone

Current laptop: ~7.5 GiB RAM, ~1.36 GiB initially available, battery initially ~38% unplugged, ~150 GiB free disk. These short CPU experiments do not validate sustained GPU speed, large training or capable language behavior. Estimates beyond 2.12M parameters/context 128 are unmeasured; source diversity, privacy filters and two-seed statistics remain limited. New test results are now public and should not become a tuning target.

Next: keep the ~1M model as baseline; run a fresh safely bounded matched-token data-size/domain-diversity ablation on AC power, with a new untouched final test suite and more seeds. Establish representative GPU acceptance measurements and complete-system quotations before requesting purchase/driver/long-job approval. No user action is required to inspect current results; GPU execution, meaningful instruction tuning and general assistant capability remain future work.
