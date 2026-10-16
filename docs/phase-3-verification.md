# Phase 2 independent verification before Phase 3

Started from clean `research/phase2-model-reliability` at `72ea4d7`. Read the delivery/evaluation/hardware/roadmap documents and inspected actual trainer/model, dataset manifests/shards and checkpoint tensors. No old training artifacts were overwritten.

The selected 984,192-parameter checkpoint reproduces **exactly** on this CPU stack: validation loss 4.403331741442086, test loss 4.1786155273320755, test perplexity 65.27541859339495. Perplexity is exp(mean natural-log token cross entropy), not exp(mean batch loss) or exp(training loss). Absolute differences from recorded validation/test losses are zero. Tensor hashes, shapes, finite values, tied weights, dataset files and mapped token shards pass verification. Source-code hash matches the run's recorded hash. Evidence: `evidence/phase3/baseline/reproduced-metrics.json`.

All original 19 tests, Ruff, TypeScript, production build, npm audit, pip consistency/audit and real browser QA were rerun before model changes. Exact commands, output, durations and exit codes: `evidence/phase3/baseline/summary.json`. Real API lifecycle QA is separately recorded under `baseline/api-e2e.json` (launch, duplicate rejection, restart persistence, 6→8-step resume, inference, cancellation).

No numerical discrepancy was found. Limitations confirmed before proceeding: old comparisons were not matched-token; old test loss was used repeatedly; validation/test were evaluated with short disjoint context windows; source-level splitting does not prevent shared concepts; code hash strictly forbids resuming after engine changes. The new cycle must freeze held-out sources/tokenizer, improve measured evaluation overhead without changing the likelihood definition, and provide an explicitly tested checkpoint migration rather than silently bypassing identity checks.

Hardware recheck is in `evidence/phase3/hardware.json`: ~7.48 GiB total RAM, ~1.36 GiB available initially, battery ~38% and unplugged, ~149.85 GiB free storage. Training remains CPU-only and bounded; no system dependency, driver or purchase is needed.
