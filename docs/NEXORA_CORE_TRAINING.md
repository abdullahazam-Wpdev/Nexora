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

## Phase 7 — completion-only tool selection

The selected `phase2-small-language` checkpoint remains 984,192 parameters and unchanged SHA-256 `0b10d349fe2a8517544cd31cee03140eba7aa730fd1087ae01f0b02b1b56ee84`. Its tokenizer, dataset identity, recorded validation/test and throughput/resource metrics are in `docs/evidence/phase7/selected-core.json`. Fresh held-out tool-selection evaluation scored 0/16 valid/correct tool responses. Earlier instruction benchmarks remain earlier evidence, not newly measured general intelligence.

`nexora/tool_sft.py` adds a separate masked-loss pilot without altering the existing engine or checkpoints. Prompt and padding labels are -100; only completion/EOS targets contribute. A test verifies the precise boundary. Original deterministic synthetic CC0 examples cover eight tool decisions (search, file read, tests, calculator, knowledge, approval, no-tool and retry), with train/validation/test IDs and version hashes. No proprietary assistant outputs or private conversations were used.

Three real 40-step CPU runs were completed, each 171,328 parameters and 1,600 supervised completion tokens. The first held out only template variants; the second deliberately uses different evaluation wording; the third reproduced the second with identical held-out loss and checkpoint tensors. Results and detailed answers are in `docs/evidence/phase7/tool-sft-*.json`. The wording-held-out run has completion-only validation loss 0.5719157085 and test loss 0.5841850132 / perplexity 1.7935286876. JSON schema validity improved from 0/16 to 16/16, but correct tool choice was only 2/16 (12.5%, chance level across eight classes). This is evidence of learning output form, not useful tool-selection ability. No checkpoint was promoted.

Checkpoint directories: `artifacts/tool-sft/phase7-tool-sft-40/`, `phase7-tool-sft-paraphrase-40/`, `phase7-tool-sft-paraphrase-repeat/`. Each retains dataset, tokenizer, model.safetensors and metrics. Model state roundtrip was verified. These use an explicit experimental format and are not silently passed through the production run loader; no checkpoint migration is needed because existing formats were untouched. Masked perplexity cannot be compared with pretraining perplexity.

```sh
# Choose an unused run ID. Do not overwrite earlier runs.
.venv/bin/python -m nexora.tool_sft --run-id phase7-tool-sft-reproduce --steps 40
```

The pilots do not train code execution, improve context length or establish instruction following. Next: richer independently held-out tool scenarios, argument accuracy, balanced classification and larger rights-reviewed data before scale or promotion.
