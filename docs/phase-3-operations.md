# Phase 3 operations and exact commands

The v3 trainer preserves the Transformer tensor layout and inference support for verified v2/v3 checkpoints. Source-code identity is strict for training; old runs are never silently relabeled or overwritten.

## Reproduction commands executed

```sh
# Before changing the trainer: original 19 tests/build/browser/dependency checks.
.venv/bin/python -c 'exec(compile(open("scripts/verify_phase2.py").read().replace("phase2/final", "phase3/baseline"),"scripts/verify_phase2.py","exec"))'
# API lifecycle script was executed with isolated phase3 store/evidence destinations.
.venv/bin/python -m scripts.phase3_benchmark
.venv/bin/python -m nexora.expansion --catalog configs/phase3-data.sources.json --base python-tutorial-bd831076dc61 --approve-download
.venv/bin/python -m nexora.scaling_experiments plan --tokens 262144 --max-seconds 240
.venv/bin/python -m nexora.scaling_experiments run
# The initial driver failed after its first completed run; corrected/recovered invocation
# verified and reused that checkpoint, then reached its time limit. Do not rerun this
# existing matrix: its persistent ledger is deliberately marked exhausted.
.venv/bin/python -m scripts.phase3_results
.venv/bin/python -m scripts.phase3_report
.venv/bin/python -m scripts.phase3_recovery
.venv/bin/python -m scripts.migrate_checkpoint phase3-baseline-s43 --id phase3-compatible-fork
.venv/bin/python -m nexora.research train phase3-compatible-fork --resume --steps 1
.venv/bin/python scripts/verify_phase3.py
```

The benchmark command was first run against the unmodified v2 implementation and later against the optimized implementation. Retained baseline and optimized evidence distinguish these runs; the current script writes the optimized benchmark file. Phase 2 metric reproduction was executed directly with verified weights and `_mapped_tokens`/`evaluate` before changes; all calculated values and hashes are retained in the baseline evidence.

The actual API lifecycle wrapper commands, outputs and statuses are referenced in the final delivery evidence. These scripts train tiny verification jobs under isolated `NEXORA_STORAGE` roots. They are not scaling-matrix candidates or capability benchmarks.

## New data and matched experiment configuration

`configs/phase3-data.sources.json` is rights-reviewed, explicitly bounded to 850 kB total and now pins every acquired source SHA-256. The actual workflow acquired/cached 282,239 bytes. It reuses approved Phase 2 training text and adds six CPython library sources; copy/textwrap are frozen test sources, stdlib remains the original validation source, and legacy controlflow test is not trained on.

Actual prepared datasets:

- `artifacts/datasets/phase3-base-ddaa35f3eeb5/`
- `artifacts/datasets/phase3-expanded-61dc5275e032/`
- `artifacts/evaluation_suites/python-sources-phase3-v1/`

All train/held-out files are hashed/versioned, source-separated, exact/near deduplicated and protected against shared 12-word shingles. Notices are retained. Source groups and operator permission assertions still require genuine review; the pipeline cannot establish legal ownership of arbitrary supplied text. Language detection remains a script heuristic. This is a small technical corpus.

Matched comparison uses context 128, batch 4, accumulation 2, fixed 1024-entry tokenizer from `phase2-small-language`, seeds 42/43, the same schedule, and immutable step-128 checkpoints (**131,072 tokens**) for all six candidates. Some runs continued to 256; those extra updates are not used in the matched comparison. The planned dataset-size ablation did not run before the cap. No effect of dataset expansion is claimed without that ablation.

## Checkpoint locations

- Original selected model: `artifacts/runs/phase2-small-language/checkpoints/step-0000400/model.safetensors` (preserved; still selected for the existing playground).
- Validation-selected Phase 3 comparison checkpoint: `artifacts/runs/phase3-baseline-s43/checkpoints/step-0000128/model.safetensors`.
- Other common checkpoints: `artifacts/runs/phase3-{compact,baseline,wider}-s{42,43}/checkpoints/step-0000128/`.
- Interrupted wider worker recovered into `artifacts/runs/phase3-wider-s43/checkpoints/step-0000130/`; step 128 remains unchanged.
- Explicit final-revision compatibility fork: `artifacts/runs/phase3-compatible-fork/checkpoints/step-0000257/`.
- Exact experimental source snapshot: directory in `evidence/phase3/training-code-snapshot.json`. It retains the code bytes corresponding to the original run source hash before the final negative-battery-input validation fix.

## Migration without data loss

```sh
.venv/bin/python -m scripts.migrate_checkpoint PARENT_RUN --id NEW_FORK_ID
.venv/bin/python -m nexora.research train NEW_FORK_ID --resume --steps 2
```

Explicit forks accept verified v2/v3 checkpoints, preserve model/optimizer/sampler/tokenizer/shards and LR schedule, and record parent checkpoint/source-code identity. They publish a new run with current code identity; the parent is untouched. v2→v3 next-update equality is tested using the actual committed v2 trainer; v3 fork equivalence and a real one-step fork of a Phase 3 artifact are also verified. A future change to numerical training semantics needs its own migration validation; the helper is not proof that arbitrary code revisions train identically.

## Resource limits and stable evaluation

Python checks keep per-step memory/disk/time/cancellation controls. Temperature reads are sampled every 0.25 seconds; low battery (<15%, unless on AC) stops training. These are monitored budgets, not hard OS memory guarantees. CPU matrix used 800 MiB RSS, 500 MiB available RAM, 85°C and 90-second per-session limits. Final framework persists a plan fingerprint/deadline; retries cannot silently renew the budget. Its exhausted original ledger is retained rather than rewritten as a successful transaction.

Final test was evaluated only after validation-based common-checkpoint selection, not on every candidate. Generation probes do not establish instruction-following. Test/source details are now public; use a new untouched final source for future tuning. Withheld test values are `null`; the only frontend edit makes the existing display tolerate that honest missing value.

No system packages, GPU drivers, paid APIs, infrastructure purchases or cloud provisioning were used. CPU PyTorch remains installed. GPU workstation decision and theoretical compute envelopes are documented separately; GPU/AMP/DDP execution is not implemented or benchmarked.
