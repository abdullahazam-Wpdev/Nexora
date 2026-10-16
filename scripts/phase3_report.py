"""Generate scaling tables/calculations only from recorded experiment evidence."""

import statistics
import json
from pathlib import Path
import numpy as np
from nexora.artifacts import atomic_json

root = Path(__file__).resolve().parent.parent
out = root / "docs/evidence/phase3"
comparison = json.loads((out / "model-comparison.json").read_text())
matrix = json.loads((out / "experiment-matrix.json").read_text())
before = json.loads((out / "baseline/performance.json").read_text())
after = json.loads((out / "optimized-performance.json").read_text())
complete = [r["result"] for r in matrix if r["exit_code"] == 0]
xs = np.array([r["parameters"] / 1e6 for r in complete])
ys = np.array([1e6 / r["benchmark"]["tokens_per_second"] for r in complete])
slope, intercept = np.polyfit(xs, ys, 1)
forecasts = []
for p in [5_000_000, 10_000_000, 30_000_000, 100_000_000]:
    seconds = max(ys.min(), float(intercept + slope * p / 1e6))
    tokens = 20 * p
    forecasts.append(
        {
            "parameters": p,
            "optimizer_model_state_gib_lower_bound": 16 * p / 1024**3,
            "weights_gib": 4 * p / 1024**3,
            "training_seconds_per_million_tokens_linear_extrapolation": seconds,
            "scenario_tokens": tokens,
            "scenario_training_hours": tokens / 1e6 * seconds / 3600,
            "scenario_range_hours_0_5x_to_3x": [
                tokens / 1e6 * seconds / 3600 * 0.5,
                tokens / 1e6 * seconds / 3600 * 3,
            ],
        }
    )
atomic_json(
    out / "cpu-scaling-estimates.json",
    {
        "measured_points": [
            {
                "parameters": r["parameters"],
                "seconds_per_million_training_tokens": 1e6
                / r["benchmark"]["tokens_per_second"],
            }
            for r in complete
        ],
        "linear_fit": {
            "slope_seconds_per_million_tokens_per_million_parameters": float(slope),
            "intercept_seconds_per_million_tokens": float(intercept),
        },
        "forecasts": forecasts,
        "warning": "Extrapolations beyond 2.12M parameters and context 128 are unmeasured. Range is a sensitivity scenario, not a confidence interval; cache/attention/precision changes can make it wrong.",
    },
)
lines = [
    "# Phase 3 foundation-model scaling report",
    "",
    "## Reverification",
    "",
    "The original 984,192-parameter checkpoint reproduces validation loss **4.403331741442086**, test loss **4.1786155273320755** and test perplexity **65.27541859339495** exactly before engine changes. Perplexity is exp(test cross entropy). Original 19 tests and relevant platform/API checks passed. See [verification](phase-3-verification.md).",
    "",
    "## Measured optimization",
    "",
    f"On the original checkpoint, monitored validation fell from {before['evaluation']['monitored']['seconds']:.3f}s to {after['evaluation']['monitored-batched']['seconds']:.3f}s. Absolute loss change is {abs(before['evaluation']['monitored']['metrics']['loss'] - after['evaluation']['monitored-batched']['metrics']['loss']):.2e}; this is FP32 reduction-order rounding, not a new model result.",
    "",
    f"Warm CPU greedy generation measured {after['warm_inference_tokens_per_second']:.1f} tokens/s for 64 new tokens, without KV cache or model-load cost. Fixed synthetic training timing measured {after['training_tokens_per_second']:.0f} tokens/s ({after['training_seconds_per_million_tokens']:.1f}s/million tokens). Real corpus run rates below were slower; do not present the synthetic rate as achieved end-to-end training throughput. Checkpoint buffered save median was {after['checkpoint_buffered_save_median_seconds']:.4f}s, warm weight read {after['checkpoint_read_seconds']:.4f}s; OS caching/durable flush/device latency are not fully represented.",
    "",
    "The main change batches equal-length evaluation windows while counting every target/remainder, and samples expensive temperature sensors at 0.25-second intervals. Memory, disk, cancellation and clock checks still run on every monitor call. Battery reserve defaults to 15%. Full exact-resume and v2 migration tests pass; model tensor layout is unchanged.",
    "",
    "## Dataset expansion",
    "",
    "A reviewed version-pinned PSF-2.0 corpus adds six CPython library sources. Total acquired/cached bytes for this workflow: 282,239; raw sources are SHA-256 pinned, license/copyright retained, and no proprietary-model output is trained on. Training text grows from 166,170 to 353,802 characters (642→1,406 documents); 18 exact duplicates were removed. Validation remains 48 original stdlib documents; final test is 60 previously unused copy/textwrap-source documents. Source/exact-document/12-word-shingle train/held-out intersections are zero in the independent audit. The old controlflow test is excluded from new training.",
    "",
    "A frozen tokenizer from the Phase 2 training-only corpus and the same hashed evaluation-suite files are used for all matrix candidates. Source-concept overlap is not eliminated by shingle filtering. This remains a small English technical corpus, not a general-language foundation-model dataset.",
    "",
    "## Matched-token comparison",
    "",
    "All six model/seed combinations have verified step-128 checkpoints: **131,072 training tokens**, context 128, vocabulary 1024, batch 4, accumulation 2, seeds 42/43 and identical LR schedule. Larger completed runs also have step-256 checkpoints; these later weights are not used for the matched comparison.",
    "",
    "| Parameters | Width / layers / heads | Mean validation loss | Mean held-out validation perplexity | Sample SD (2 seeds) |",
    "| ---: | --- | ---: | ---: | ---: |",
]
for g in comparison["groups"]:
    r = next(r for r in comparison["comparison"] if r["parameters"] == g["parameters"])
    c = r["architecture"]
    lines.append(
        f"| {g['parameters']:,} | {c['dim']} / {c['layers']} / {c['heads']} | {g['validation_mean']:.4f} | {statistics.mean(x['validation']['perplexity'] for x in comparison['comparison'] if x['parameters'] == g['parameters']):.2f} | {g['validation_sample_std']:.4f} |"
    )
sel = comparison["selected"]
test = comparison["selected_test"]
lines += [
    "",
    f"Validation-based selection: `{sel['run_id']}`, **step 128**, then one final held-out test: loss **{test['loss']:.6f}**, perplexity **{test['perplexity']:.4f}**, {test['tokens']:,} targets. Selection was written before test evaluation in `selection-before-test.json`.",
    "",
    "The 2.12M model did not beat the 984K model at this budget. This is evidence against blindly increasing width under severe token/compute limits, not a universal scaling law. Two seeds and one narrow validation source do not establish statistical significance or broad domain performance. The previous Phase 2 score used more training tokens and a different test source; its perplexity cannot be directly compared with the new final test value. The existing served Phase 2 model was not automatically replaced.",
    "",
    "## Actual runtime and budgets",
    "",
    "| Run | Completed optimizer steps at matrix stop | Training-only tokens/s | Training seconds / million tokens | Run wall seconds | Peak process RSS MiB | Checkpoint save seconds (sum) |",
    "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
]
for item in matrix:
    r = item["result"]
    b = r.get("benchmark")
    res = r["resources"]
    if b:
        values = [
            str(r["steps"]),
            f"{b['tokens_per_second']:.0f}",
            f"{1e6 / b['tokens_per_second']:.1f}",
            f"{res['wall_seconds']:.2f}",
            f"{res['peak_rss_mb']:.1f}",
            f"{b['checkpoint_save_seconds']:.4f}",
        ]
    else:
        values = [
            f"{r['steps']} published; interrupted",
            "not fully recorded",
            "not fully recorded",
            f"{res['wall_seconds']:.2f} at last progress snapshot",
            f"{res['peak_rss_mb']:.1f}",
            "not fully recorded",
        ]
    lines.append("| " + r["id"] + " | " + " | ".join(values) + " |")
lines += [
    "",
    "Hardware probes selected the three configurations using measured RSS/throughput, not arbitrary training-size targets. Probes underestimated sustained runtime. The recovered driver hit its **240-second invocation cap**, interrupting the final wider worker. An initial controller-variable error had already completed the first compact run; that run was verified and reused rather than overwritten. Including that earlier failed-controller attempt, total research wall effort exceeded 240 seconds; the cap was not a transaction-wide timer across both invocations. No individual matrix worker exceeded 90 seconds, process limits were 800 MiB RSS / 500 MiB available RAM / 85°C CPU, and measured CPU temperature peaked at 72°C. The planned data-size ablation was not run; no causal benefit of extra data is claimed. The final framework now persists its plan fingerprint and deadline across retries, with an automated regression test; the historical timings above are not retroactively changed. Future plans should use sustained measurements and larger contingency margins.",
    "",
    "The interrupted run was verified at step 128 and resumed for exactly two recovery-test updates (to 130), preserving the original comparison checkpoint. A separate real SIGKILL recovery test, final-code migration fork and actual API-restart/cancel checks are recorded separately; these short verification jobs are not additional scaling-matrix candidates.",
    "",
    "## Generation, memorization and capability",
    "",
    "Generation diagnostics measure repetition, distinct words/bigrams, capped longest exact spans, three train-prefix and three validation-prefix completions, and four strict formatting/arithmetic instruction probes. The validation-selected step-128 model scored **0/4** on those instruction probes. It emits fragments/repetition and is not a demonstrated assistant, coder or reasoner. Exact-match probes do not establish absence of semantic memorization. Diagnostics are never recycled as training data. Full outputs are retained in `generation-quality.json`.",
    "",
    "## CPU scaling estimates",
    "",
    "These calculations fit seconds/million tokens against the **measured full-run training-only rates**, then extrapolate beyond the largest observed 2.12M model. They omit evaluation, preprocessing, unsaved work, scheduling delays and changed vocabulary/context. The 0.5×–3× range is a sensitivity scenario, not a statistical confidence interval. No hours-long job was started.",
    "",
    "| Future parameters | FP32 weights/gradients/Adam lower bound GiB | Estimated training seconds / million tokens | Illustrative 20 tokens/parameter workload | Kernel-only hours |",
    "| ---: | ---: | ---: | ---: | ---: |",
]
for f in forecasts:
    lines.append(
        f"| {f['parameters']:,} | {f['optimizer_model_state_gib_lower_bound']:.2f} | {f['training_seconds_per_million_tokens_linear_extrapolation']:.0f} | {f['scenario_tokens']:,} tokens | {f['scenario_training_hours']:.1f} |"
    )
lines += [
    "",
    "State memory excludes activations, workspaces, CPU/Python runtime and checkpoint buffers. Observed 2.12M process RSS was ~432 MiB despite ~32 MiB of parameter/optimizer state; do not scale RSS from weight bytes alone. More RAM helps headroom but does not remove multi-hour/day CPU compute costs. The engine still caps CPU models at 5M parameters and no larger models were allocated or trained.",
    "",
    "## Recommended next milestone",
    "",
    "Keep the ~1M model as the research baseline. Improve source diversity and domain-matched evaluation; compare data expansion at a genuinely fixed token budget before widening again. Use an untouched new test suite for future tuning cycles because this test score is now public. Repeat more seeds and benchmark on AC power with a persistent aggregate deadline. GPU purchase decisions should follow a representative measured GPU acceptance benchmark, a licensed token plan and explicit budget; see [workstation decision](gpu-workstation-decision.md).",
]
(root / "docs/phase-3-scaling-report.md").write_text("\n".join(lines) + "\n")
print("Scaling report and extrapolation evidence written")
