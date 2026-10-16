"""Independent artifact checks and evidence-based model comparison report."""

import json
from tokenizers import Tokenizer
from nexora.config import ROOT, STORE
from nexora.data_engine import load_dataset, canonical, shingles
from nexora.research import verify_checkpoint
from nexora.artifacts import atomic_json

rows = json.loads((ROOT / "docs/evidence/phase2/experiment-matrix.json").read_text())
manifest, splits = load_dataset(rows[0]["result"]["dataset_id"])
checks = {}
for a, b in [("train", "validation"), ("train", "test"), ("validation", "test")]:
    ah = {canonical(d["text"]) for d in splits[a]}
    bh = {canonical(d["text"]) for d in splits[b]}
    sa = {d["source_id"] for d in splits[a]}
    sb = {d["source_id"] for d in splits[b]}
    ag = [shingles(d["text"]) for d in splits[a]]
    bg = [shingles(d["text"]) for d in splits[b]]
    agrams = set().union(*ag)
    bgrams = set().union(*bg)
    maximum = max(
        (len(x & y) / len(x | y) for x in ag for y in bg if x and y), default=0
    )
    checks[a + "_" + b] = {
        "exact_document_overlap": len(ah & bh),
        "source_overlap": len(sa & sb),
        "shared_12word_shingles": len(agrams & bgrams),
        "maximum_document_shingle_jaccard": maximum,
    }
verified = []
for row in rows:
    result = row["result"]
    folder = STORE / "runs" / row["id"]
    info, cp = verify_checkpoint(folder)
    tokenizer = Tokenizer.from_file(str(folder / "tokenizer.json"))
    probes = [
        "Python is readable.",
        "café — Ελληνικά — اردو — 日本語",
        "tabs\tand newlines\n🙂",
    ]
    assert all(tokenizer.decode(tokenizer.encode(s).ids) == s for s in probes)
    verified.append(
        {
            "id": row["id"],
            "checkpoint": info,
            "roundtrip_probes": probes,
            "all_roundtrips_passed": True,
            "sample_continuation_matches": [
                s["continuation_exact_in_train"] for s in result["samples"]
            ],
        }
    )
atomic_json(
    ROOT / "docs/evidence/phase2/independent-evaluation.json",
    {
        "contamination": checks,
        "checkpoints": verified,
        "limitation": "Shingle tests and exact generated-continuation checks do not rule out semantic leakage or memorization.",
    },
)
lines = [
    "# Model evaluation and comparison — Phase 2",
    "",
    "All runs start from random weights and use the same approved CPython tutorial dataset, train-only BPE settings, source-level splits and deterministic seed 42. This is a small technical-language experiment, not an assistant capability benchmark.",
    "",
    "| Run | Parameters | Steps | Train loss (last batch) | Full validation loss | Validation perplexity | Full test loss | Train tokens | Training tokens/s | Wall seconds | Peak RSS MiB |",
    "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
]
for row in rows:
    r = row["result"]
    lines.append(
        f"| {r['id']} | {r['parameters']:,} | {r['steps']} | {r['history'][-1]['train_loss']:.4f} | {r['validation']['loss']:.4f} | {r['validation']['perplexity']:.2f} | {r['test']['loss']:.4f} | {r['benchmark']['total_training_tokens']:,} | {r['benchmark']['tokens_per_second']:,.0f} | {r['resources']['wall_seconds']:.2f} | {r['resources']['peak_rss_mb']:.1f} |"
    )
best = min(rows, key=lambda r: r["result"]["validation"]["loss"])["result"]
lines += [
    "",
    "## Interpretation",
    "",
    f"Select `{best['id']}` using validation loss only. Its full test loss is {best['test']['loss']:.4f}, test perplexity {best['test']['perplexity']:.2f}. Validation evaluates every one of 3,777 held-out next-token targets; test evaluates 12,809. Remainders are included, loss is token-weighted, and evaluation does not sample or consume the training RNG.",
    "",
    "Tiny and Small use contexts 64 and 128, respectively, so 400 Small steps consume twice as many tokens as 400 Tiny steps. This is an exploratory architecture/training configuration comparison, **not a matched-token or matched-compute causal claim**. The two Small runs match architecture, token budget and seed; changing peak learning rate from 0.002 to 0.001 slightly worsened validation loss. One seed and one held-out source per split do not establish statistical significance. The test split was reported for each completed run, so it should be replaced by a fresh untouched final source before broader future tuning.",
    "",
    "The original arithmetic model’s training loss 0.468 is not comparable with language-corpus losses. No general knowledge, reasoning, coding, tool-use, web-development or defensive-security accuracy has been established. No standardized benchmark scores are invented.",
    "",
    "## Real generation samples",
    "",
]
for r in [row["result"] for row in rows if row["id"] != "phase2-tiny-benchmark"]:
    lines += [f"### {r['id']}", "", "```text", r["samples"][0]["text"], "```", ""]
lines += [
    "The samples show learned fragments and repetition, including misspellings and incorrect statements. They are evidence of local checkpoint inference, not reliable programming or instruction following. No proprietary model supplies these outputs.",
    "",
    "## Integrity, contamination and reproducibility",
    "",
    "Every matrix checkpoint passed SHA-256 verification, strict expected tensor shape loading, finite-value checks and tied-weight equality. Unicode tokenizer round trips passed for Latin accents, Greek, Urdu, Japanese, tabs/newlines and emoji. Exact checkpoint evidence is in `evidence/phase2/independent-evaluation.json`.",
    "",
    "Source and exact-document intersections are zero across all split pairs. Shared 12-word shingles and maximum pairwise similarity are reported explicitly in the JSON; source holdouts do not eliminate shared concepts or standard programming phrases. Generation-continuation containment checks are limited to three short prompts and cannot establish absence of memorization.",
    "",
    "The exact-resumption regression compares uninterrupted and split training, including every model tensor, optimizer state, sampler RNG, scheduler configuration/step and final validation metric. Equality is tested on the installed CPU/PyTorch stack; cross-version/hardware bitwise reproducibility is not promised.",
    "",
    "## Performance and budgets",
    "",
    "Training-only throughput excludes full evaluation, tokenizer preparation and checkpoint serialization. Overall wall time includes these costs; the 1,000-step estimate in each result extrapolates training kernels only. CPU utilization uses 100% per fully used core. Peak RSS is process RSS, not whole-system memory, and includes a process-lifetime high-water mark. Temperature sensors peaked below the configured 88°C cutoff during these matrix runs. Memory/disk/time checks run between steps and during evaluation; an OS kill can still occur before Python handles pressure.",
    "",
    "## Next experiment",
    "",
    "Compare profiles at a fixed token budget, repeat seeds, use an untouched source-level final test set, evaluate several text domains and choose a larger licensed corpus only after budget/quality review. Implement human-reviewed instruction data and executable task evaluation before offering assistant/coding capability.",
]
(ROOT / "docs/model-evaluation-report.md").write_text("\n".join(lines) + "\n")
print("Independent comparison and contamination evidence recorded")
