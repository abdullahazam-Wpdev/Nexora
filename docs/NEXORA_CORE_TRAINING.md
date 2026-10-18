# NEXORA Core training — current state and roadmap pointer

NEXORA Core is this project's own independently trained foundation model --
never a relabeled external checkpoint. The full, already-verified history is
in [phase-2-delivery.md](phase-2-delivery.md), [phase-3-delivery.md](phase-3-delivery.md),
[phase-3-scaling-report.md](phase-3-scaling-report.md),
[dataset-strategy.md](dataset-strategy.md) and [roadmap.md](roadmap.md). This
page is the Phase 4 pointer plus what changed now.

## Current state (unchanged by this pass)

- Architecture: tiny CPU transformer, currently up to ~2.12M parameters in
  compared configurations; width/depth/context are explicit and bounded by
  the API.
- Tokenization, dataset provenance, deduplication and held-out evaluation are
  implemented and tested (`tests/test_core.py`, `tests/test_phase3.py`).
- Checkpoints are versioned and exact-resumable; migration between dataset
  versions is tested (`scripts/migrate_checkpoint.py`).
- No instruction-following, tool-use, or retrieval-augmented capability has
  been demonstrated -- see [model-evaluation-report.md](model-evaluation-report.md).

## Model identifier separation

`nexora/provider_registry.py` keeps NEXORA Core (`id: core`, `training: true`)
strictly separate from every external/hosted entry (`training: false`
everywhere else, including the new `nvidia-nim` row). No external checkpoint,
including the untested NVIDIA Nemotron-3-Nano-4B GGUF staged for
storage-only download by `scripts/download-nvidia-reference.py`, is ever
labeled as NEXORA-trained or loaded as Core.

## Phase 5 update

A real bounded instruction-following pilot ran this pass:
`phase5-instruction-pilot-v1`, 918,656 parameters, trained on a new
original 61-document dataset. It is **evaluated and not promoted** --
`artifacts/selected-model.json` is unchanged. Full results, including a
caught train/eval contamination issue, are in
`docs/INSTRUCTION_TUNING.md`. An architecture review found no evidence-
justified reason to change `nexora/model.py`; see
`docs/NEXORA_TRAINING_STRATEGY.md`.

## What this pass adds to the roadmap

Nothing changed in Core's architecture, data pipeline, or checkpoints this
session. The explicit next step toward "NEXORA Core capable of operating the
agent runtime itself" (Phase 4 §7) is unchanged from `roadmap.md`: a matched-
token data-size ablation, human-reviewed instruction data, and a bounded
tool-use training experiment -- each gated by evaluation before promotion,
per the pipeline in [research-operations.md](research-operations.md). That
work was not started in this pass; it needs a dedicated, separately-approved
training budget rather than being folded into an infrastructure/integration
pass.
