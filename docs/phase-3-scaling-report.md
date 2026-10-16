# Phase 3 foundation-model scaling report

## Reverification

The original 984,192-parameter checkpoint reproduces validation loss **4.403331741442086**, test loss **4.1786155273320755** and test perplexity **65.27541859339495** exactly before engine changes. Perplexity is exp(test cross entropy). Original 19 tests and relevant platform/API checks passed. See [verification](phase-3-verification.md).

## Measured optimization

On the original checkpoint, monitored validation fell from 1.800s to 0.112s. Absolute loss change is 7.27e-08; this is FP32 reduction-order rounding, not a new model result.

Warm CPU greedy generation measured 340.1 tokens/s for 64 new tokens, without KV cache or model-load cost. Fixed synthetic training timing measured 10737 tokens/s (93.1s/million tokens). Real corpus run rates below were slower; do not present the synthetic rate as achieved end-to-end training throughput. Checkpoint buffered save median was 0.0196s, warm weight read 0.0012s; OS caching/durable flush/device latency are not fully represented.

The main change batches equal-length evaluation windows while counting every target/remainder, and samples expensive temperature sensors at 0.25-second intervals. Memory, disk, cancellation and clock checks still run on every monitor call. Battery reserve defaults to 15%. Full exact-resume and v2 migration tests pass; model tensor layout is unchanged.

## Dataset expansion

A reviewed version-pinned PSF-2.0 corpus adds six CPython library sources. Total acquired/cached bytes for this workflow: 282,239; raw sources are SHA-256 pinned, license/copyright retained, and no proprietary-model output is trained on. Training text grows from 166,170 to 353,802 characters (642→1,406 documents); 18 exact duplicates were removed. Validation remains 48 original stdlib documents; final test is 60 previously unused copy/textwrap-source documents. Source/exact-document/12-word-shingle train/held-out intersections are zero in the independent audit. The old controlflow test is excluded from new training.

A frozen tokenizer from the Phase 2 training-only corpus and the same hashed evaluation-suite files are used for all matrix candidates. Source-concept overlap is not eliminated by shingle filtering. This remains a small English technical corpus, not a general-language foundation-model dataset.

## Matched-token comparison

All six model/seed combinations have verified step-128 checkpoints: **131,072 training tokens**, context 128, vocabulary 1024, batch 4, accumulation 2, seeds 42/43 and identical LR schedule. Larger completed runs also have step-256 checkpoints; these later weights are not used for the matched comparison.

| Parameters | Width / layers / heads | Mean validation loss | Mean held-out validation perplexity | Sample SD (2 seeds) |
| ---: | --- | ---: | ---: | ---: |
| 172,352 | 64 / 2 / 4 | 5.2703 | 194.48 | 0.0134 |
| 984,192 | 128 / 4 / 4 | 5.0696 | 159.46 | 0.0938 |
| 2,115,264 | 192 / 4 / 6 | 5.1516 | 172.90 | 0.0661 |

Validation-based selection: `phase3-baseline-s43`, **step 128**, then one final held-out test: loss **4.873530**, perplexity **130.7818**, 4,639 targets. Selection was written before test evaluation in `selection-before-test.json`.

The 2.12M model did not beat the 984K model at this budget. This is evidence against blindly increasing width under severe token/compute limits, not a universal scaling law. Two seeds and one narrow validation source do not establish statistical significance or broad domain performance. The previous Phase 2 score used more training tokens and a different test source; its perplexity cannot be directly compared with the new final test value. The existing served Phase 2 model was not automatically replaced.

## Actual runtime and budgets

| Run | Completed optimizer steps at matrix stop | Training-only tokens/s | Training seconds / million tokens | Run wall seconds | Peak process RSS MiB | Checkpoint save seconds (sum) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| phase3-compact-s42 | 256 | 20111 | 49.7 | 16.64 | 350.6 | 0.0950 |
| phase3-compact-s43 | 256 | 22355 | 44.7 | 14.61 | 351.8 | 0.0732 |
| phase3-baseline-s42 | 256 | 6975 | 143.4 | 45.17 | 392.4 | 0.2990 |
| phase3-baseline-s43 | 256 | 7214 | 138.6 | 43.62 | 392.1 | 0.2726 |
| phase3-wider-s42 | 256 | 4653 | 214.9 | 67.03 | 431.8 | 0.4293 |
| phase3-wider-s43 | 128 published; interrupted | not fully recorded | not fully recorded | 31.92 at last progress snapshot | 431.8 | not fully recorded |

Hardware probes selected the three configurations using measured RSS/throughput, not arbitrary training-size targets. Probes underestimated sustained runtime. The recovered driver hit its **240-second invocation cap**, interrupting the final wider worker. An initial controller-variable error had already completed the first compact run; that run was verified and reused rather than overwritten. Including that earlier failed-controller attempt, total research wall effort exceeded 240 seconds; the cap was not a transaction-wide timer across both invocations. No individual matrix worker exceeded 90 seconds, process limits were 800 MiB RSS / 500 MiB available RAM / 85°C CPU, and measured CPU temperature peaked at 72°C. The planned data-size ablation was not run; no causal benefit of extra data is claimed. The final framework now persists its plan fingerprint and deadline across retries, with an automated regression test; the historical timings above are not retroactively changed. Future plans should use sustained measurements and larger contingency margins.

The interrupted run was verified at step 128 and resumed for exactly two recovery-test updates (to 130), preserving the original comparison checkpoint. A separate real SIGKILL recovery test, final-code migration fork and actual API-restart/cancel checks are recorded separately; these short verification jobs are not additional scaling-matrix candidates.

## Generation, memorization and capability

Generation diagnostics measure repetition, distinct words/bigrams, capped longest exact spans, three train-prefix and three validation-prefix completions, and four strict formatting/arithmetic instruction probes. The validation-selected step-128 model scored **0/4** on those instruction probes. It emits fragments/repetition and is not a demonstrated assistant, coder or reasoner. Exact-match probes do not establish absence of semantic memorization. Diagnostics are never recycled as training data. Full outputs are retained in `generation-quality.json`.

## CPU scaling estimates

These calculations fit seconds/million tokens against the **measured full-run training-only rates**, then extrapolate beyond the largest observed 2.12M model. They omit evaluation, preprocessing, unsaved work, scheduling delays and changed vocabulary/context. The 0.5×–3× range is a sensitivity scenario, not a statistical confidence interval. No hours-long job was started.

| Future parameters | FP32 weights/gradients/Adam lower bound GiB | Estimated training seconds / million tokens | Illustrative 20 tokens/parameter workload | Kernel-only hours |
| ---: | ---: | ---: | ---: | ---: |
| 5,000,000 | 0.07 | 481 | 100,000,000 tokens | 13.4 |
| 10,000,000 | 0.15 | 922 | 200,000,000 tokens | 51.2 |
| 30,000,000 | 0.45 | 2684 | 600,000,000 tokens | 447.4 |
| 100,000,000 | 1.49 | 8854 | 2,000,000,000 tokens | 4919.1 |

State memory excludes activations, workspaces, CPU/Python runtime and checkpoint buffers. Observed 2.12M process RSS was ~432 MiB despite ~32 MiB of parameter/optimizer state; do not scale RSS from weight bytes alone. More RAM helps headroom but does not remove multi-hour/day CPU compute costs. The engine still caps CPU models at 5M parameters and no larger models were allocated or trained.

## Recommended next milestone

Keep the ~1M model as the research baseline. Improve source diversity and domain-matched evaluation; compare data expansion at a genuinely fixed token budget before widening again. Use an untouched new test suite for future tuning cycles because this test score is now public. Repeat more seeds and benchmark on AC power with a persistent aggregate deadline. GPU purchase decisions should follow a representative measured GPU acceptance benchmark, a licensed token plan and explicit budget; see [workstation decision](gpu-workstation-decision.md).
