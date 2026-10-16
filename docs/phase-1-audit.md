# Independent audit of commit 6d3b60f

Audit started 2026-10-16 on branch research/phase2-model-reliability. Working tree was clean. Original root commit verified as 6d3b60fff256b5a59c59c4995cc2eecc5b81891c. Original code and trained checkpoint preserved.

## Reverified before improvements

Evidence: `docs/evidence/phase2/baseline/summary.json` contains exact commands, stdout, stderr, exit codes and durations. Eight pytest tests, TypeScript check, production build, npm vulnerability audit, pip dependency consistency and browser QA all exited 0. Checkpoint inspection is in `baseline/checkpoint.json`.

Current artifact: 143,808 parameters, step 170, 19 tensor entries, 17 optimizer states; safetensors and resume weights agree tensor-for-tensor. Train/validation/test contain 102/13/13 unique arithmetic documents, with zero exact document overlap. Source construction uses PyTorch random initialization, locally trained BPE and no pretrained checkpoint imports. The stored history agrees with previous results, but historical chronology cannot be independently proven from unsigned self-reported files.

0.467866 is a sampled **training** loss. Validation was 1.076080 and test 1.151963 on sampled batches. Real checkpoint generation begins `2 + 3 = -1.` and makes other arithmetic errors. It is not a working general assistant.

## Critical weaknesses and repair requirements

1. Fresh runs overwrite a single artifact directory; concurrent CLI/API writers are not coordinated. Add unique immutable run identities, process/file locking, atomic checkpoint publication and durable job status.
2. Validation/test use one RNG-dependent random batch. Evaluation perturbs the training RNG, so an interrupted run is not guaranteed identical to uninterrupted training. Add deterministic full-token evaluation and isolated batch RNG restored exactly, including scheduler configuration/state.
3. Dataset ingestion exists but training ignores ingested data. Add versioned datasets selected by ID, source-level holdouts, tokenizer/data hashes and bounded mapped token shards.
4. BPE is retrained unnecessarily on resume; tokenizer, corpus and code versions are not validated. Check all checkpoint inputs before resume.
5. No runtime/time/disk/thermal guard; memory checked only when API launches. Add per-step monitored budgets and failure status, periodic recovery checkpoints, nonfinite loss/gradient checks.
6. Sensitive-data filtering is rudimentary and dataset license fields are only assertions. Add source/license review records, conservative rejection and explicit source acquisition limits. Do not claim automatic legal verification.
7. No throughput, peak memory or full evaluation comparison. Add measured benchmark matrix and checkpoint integrity/memorization reports.
8. Localhost origin guard does not check Host, so DNS rebinding protection is incomplete. Add trusted-host validation and bounded control-plane inputs. No arbitrary shell execution endpoints exist.

Architecture's RoPE, RMSNorm, causal SDPA, SwiGLU and finite gradients are sound under existing tests. Preserve default layout for old checkpoints. Add optional scaled normal initialization, tied embeddings and optimizer decay groups under new configurations, with regression tests.

## Infrastructure correction

Podman is absent in the Flatpak PATH but **installed on Fedora host**, version 5.8.7, rootless with SELinux and cgroup v2. `flatpak-spawn --host` works through the existing authorized host interface. Compose provider absent initially; project-local provider can be used without privileged installation. Runtime tests are recorded separately.

## Next experiment

Use small human-authored, explicitly licensed technical text (CPython tutorial under PSF-2.0, retaining notices). First benchmark baseline/tiny and a modest small model with fixed tokens and time/memory/thermal budgets. Do not infer general reasoning/coding capability from technical-text loss. No large model or hours-long job is authorized by this cycle.

## Repair completion

The required reliability repairs were implemented and verified before the bounded language experiments. Final outcomes, evidence and remaining limits are in [Phase 2 delivery](phase-2-delivery.md) and [research operations](research-operations.md).
