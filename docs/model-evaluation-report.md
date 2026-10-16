# Model evaluation and comparison — Phase 2

All runs start from random weights and use the same approved CPython tutorial dataset, train-only BPE settings, source-level splits and deterministic seed 42. This is a small technical-language experiment, not an assistant capability benchmark.

| Run | Parameters | Steps | Train loss (last batch) | Full validation loss | Validation perplexity | Full test loss | Train tokens | Training tokens/s | Wall seconds | Peak RSS MiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| phase2-tiny-benchmark | 172,352 | 20 | 6.4521 | 6.4035 | 603.94 | 6.4055 | 10,240 | 21,541 | 13.50 | 340.8 |
| phase2-tiny-language | 172,352 | 400 | 4.1313 | 4.7333 | 113.67 | 4.6071 | 204,800 | 21,400 | 47.14 | 343.3 |
| phase2-small-language | 984,192 | 400 | 3.1879 | 4.4033 | 81.72 | 4.1786 | 409,600 | 9,170 | 71.38 | 396.6 |
| phase2-small-low-lr | 984,192 | 400 | 3.4659 | 4.4445 | 85.16 | 4.2744 | 409,600 | 9,327 | 70.59 | 395.7 |

## Interpretation

Select `phase2-small-language` using validation loss only. Its full test loss is 4.1786, test perplexity 65.28. Validation evaluates every one of 3,777 held-out next-token targets; test evaluates 12,809. Remainders are included, loss is token-weighted, and evaluation does not sample or consume the training RNG.

Tiny and Small use contexts 64 and 128, respectively, so 400 Small steps consume twice as many tokens as 400 Tiny steps. This is an exploratory architecture/training configuration comparison, **not a matched-token or matched-compute causal claim**. The two Small runs match architecture, token budget and seed; changing peak learning rate from 0.002 to 0.001 slightly worsened validation loss. One seed and one held-out source per split do not establish statistical significance. The test split was reported for each completed run, so it should be replaced by a fresh untouched final source before broader future tuning.

The original arithmetic model’s training loss 0.468 is not comparable with language-corpus losses. No general knowledge, reasoning, coding, tool-use, web-development or defensive-security accuracy has been established. No standardized benchmark scores are invented.

## Real generation samples

### phase2-tiny-language

```text
Python is
therererererererererererererererererererererererererererererere
```

### phase2-small-language

```text
Python is
contual environment, and are not handless the file is
therentation.  There is av
```

### phase2-small-low-lr

```text
Python is aviiied to the
theree.  There is a list of the module is after the
therent.
```

The samples show learned fragments and repetition, including misspellings and incorrect statements. They are evidence of local checkpoint inference, not reliable programming or instruction following. No proprietary model supplies these outputs.

## Integrity, contamination and reproducibility

Every matrix checkpoint passed SHA-256 verification, strict expected tensor shape loading, finite-value checks and tied-weight equality. Unicode tokenizer round trips passed for Latin accents, Greek, Urdu, Japanese, tabs/newlines and emoji. Exact checkpoint evidence is in `evidence/phase2/independent-evaluation.json`.

Source and exact-document intersections are zero across all split pairs. Shared 12-word shingles and maximum pairwise similarity are reported explicitly in the JSON; source holdouts do not eliminate shared concepts or standard programming phrases. Generation-continuation containment checks are limited to three short prompts and cannot establish absence of memorization.

The exact-resumption regression compares uninterrupted and split training, including every model tensor, optimizer state, sampler RNG, scheduler configuration/step and final validation metric. Equality is tested on the installed CPU/PyTorch stack; cross-version/hardware bitwise reproducibility is not promised.

## Performance and budgets

Training-only throughput excludes full evaluation, tokenizer preparation and checkpoint serialization. Overall wall time includes these costs; the 1,000-step estimate in each result extrapolates training kernels only. CPU utilization uses 100% per fully used core. Peak RSS is process RSS, not whole-system memory, and includes a process-lifetime high-water mark. Temperature sensors peaked below the configured 88°C cutoff during these matrix runs. Memory/disk/time checks run between steps and during evaluation; an OS kill can still occur before Python handles pressure.

## Next experiment

Compare profiles at a fixed token budget, repeat seeds, use an untouched source-level final test set, evaluate several text domains and choose a larger licensed corpus only after budget/quality review. Implement human-reviewed instruction data and executable task evaluation before offering assistant/coding capability.
