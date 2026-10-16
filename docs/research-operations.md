# Research operations and contracts

## Working modules

- `data_engine.py`: curated source discovery/review manifest, bounded pinned download, RST extraction, normalization, conservative privacy/quality filtering, deduplication, source-held-out immutable dataset files and quality reports.
- `research.py`: train-only byte BPE, separate mapped uint16 shards, configurable Tiny/Small profiles, optional scaled normal initialization and tied embeddings, RMSNorm/RoPE/causal SDPA/SwiGLU, AdamW decay/no-decay groups, warmup/cosine schedule, gradient accumulation/clipping, per-step history, full held-out evaluation and bounded CPU training.
- `artifacts.py`: path-ID validation, chunked SHA-256, atomic/fsynced JSON and file locks. Legacy and research trainers share `.training.lock`.
- `jobs.py`: detached local workers, PID plus process-start identity, durable launch/status records, cancellation flags and stale-worker detection. Resume-launch windows count as active jobs; another API process cannot start a competing worker through the control lock.
- `research_api.py`: real selectable datasets/runs, start/resume/cancel/status/checkpoint/inference/selection APIs. Source downloading remains CLI-only; no arbitrary terminal execution or third-party account access is enabled.
- `scaling.py`: planning-only parameter/memory/FLOP calculator for future hardware. CUDA/AMP/DDP execution is not implemented or claimed.

The frontend was not redesigned. Existing API lists show actual completed research experiments and dataset metadata. `/api/training` now dispatches versioned research jobs rather than overwriting the original checkpoint. `/api/generate` uses an explicitly selected research model, or the original arithmetic checkpoint when no model is selected. For precise run identity/advanced operations use the research API; some original frontend labels still describe the bootstrap Tiny model.

## Artifact layout

```
NEXORA_STORAGE/
  raw/<source-catalog>/<source-id>
  datasets/<name>-<content-version>/
    manifest.json, quality.json, acquisition.json
    train.jsonl, validation.jsonl, test.jsonl
  runs/<unique-id>/
    result.json, launch.json, job.log
    tokenizer.json, tokens.json
    train.npy, validation.npy, test.npy
    latest.json
    checkpoints/step-0000100/
      checkpoint.json, model.safetensors, resume.pt
  selected-model.json
  nexora.db
  tiny-core/                 # original artifact preserved
```

No large datasets/checkpoints enter Git. A fresh run cannot overwrite an existing run. Published checkpoint directories are immutable; a completed step is announced only by atomically replacing latest.json after publishing the bundle. An abrupt crash can leave an unreferenced staging directory; do not delete it before checking recovery needs. JSON publication is fsynced; weights/optimizer file power-loss durability is not equivalent to a fully transactional filesystem snapshot.

## Exact resumption

Store model configuration, dataset version, tokenizer/shard hashes, source-code hash, Git commit+dirty flag, training configuration, optimizer state, training sampler RNG, PyTorch RNG and scheduler step/configuration. Resume requires the same versioned training implementation and configuration. Separate sampler RNG and deterministic full evaluation prevent stop-boundary evaluation from changing future batches. Periodic checkpoints bound recoverable work; cancellation/resource stops may roll back unsaved steps on resume. No arbitrary automatic config migration is allowed.

CPU equality is verified for uninterrupted vs split training. Cross-platform/PyTorch-version and future GPU equality are not promised. Code changes require a new run; checkpoint inference remains available. Run forking into a changed configuration is planned.

## Budgets and job lifecycle

Default train control: <=2,000 requested steps per invocation, <=600 seconds, <=4 CPU threads, bounded batches/accumulation/vocabulary, process RSS and available-memory floor, free-disk floor, thermal threshold, and nonfinite loss/gradient rejection. Matrix used stricter 120-second/900-MiB-RSS/500-MiB-available limits. These are Python monitors, not hard cgroup quotas; an allocation or OS kill can happen before a check. API workers record stopped/failed status and diagnostics, and last valid checkpoint remains separate from status.

API restart does not kill detached training workers. PID reuse is guarded with process creation time. Abrupt worker death is displayed as interrupted and resumable when a checkpoint exists. There is no automatic supervisor restart or distributed queue. On request, cancellation creates a flag checked during training/evaluation; it never signals an unverified PID. A process interrupted before its first checkpoint cannot resume that run.

Identity remains `local-owner`; Host and browser Origin validation protect local browser access but do not provide user authentication. Public deployment remains disabled. Keep one API worker per workspace. API launch rejects a concurrent active job and uses the same training lock as CLI; a race with an external direct CLI contender can fail one worker before it acquires the lock, leaving explicit failed/queued diagnostics rather than corrupting a shared checkpoint.

## Remaining research gaps

The corpus is tiny, technical and English-heavy. RST extraction is conservative rather than a full parser; script heuristics are not language identification; privacy/quality rules are incomplete and can reject benign examples. Near-dedup is quadratic and intentionally bounded to small corpora. The model has no KV cache, sampling controls, instruction tuning, retrieval or tools. Evaluate general language and executable tasks before calling it a capable assistant.

PostgreSQL and Redis are working optional infrastructure, not active persistence/queue adapters for this API. SQLite remains authoritative for projects/memory/audit. No public listener, payment, model API or external account has been enabled.
