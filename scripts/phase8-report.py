"""Render research tables from measured public evidence; never estimate observed metrics."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
folder = ROOT / "docs/evidence/phase8"
matrix = json.loads((folder / "core-matrix.json").read_text())["runs"]
selected = json.loads((folder / "selected-core.json").read_text())
rows = []
for r in matrix:
    rows.append(
        f"| {r['id']} | {r['parameters']:,} | {r['training_completion_tokens']} | {r['validation']['completion_loss']:.6f} | {r['test']['completion_perplexity']:.6f} | {r['quality']['tool_success']}/16 | {r['quality']['schema_valid']}/16 | {r['training_seconds']:.3f} | {r['resources']['peak_rss_mb']:.1f} |"
    )
text = """# Measured Core study

Selected Core is unchanged: 984,192 parameters, original PSF technical corpus,
BPE tokenizer, RoPE/RMSNorm/SwiGLU decoder. Training count remains 409,600 tokens.
Checkpoint SHA-256 is `0b10d349fe2a8517544cd31cee03140eba7aa730fd1087ae01f0b02b1b56ee84`.
Phase 8 batched evaluation reproduces validation loss **%.9f**, test loss
**%.9f**, perplexity **%.9f**. Perplexity is exp(test cross entropy).
Differences of less than 1e-6 from the older scalar evaluation are floating-point
reduction order, not a changed checkpoint or model improvement. Strict instruction
probes remain **0/4**. See selected-core.json for actual generated text.

Four new randomly initialized completion-only pilots share tokenizer, data,
seed 42, context 128, 40 steps and 1,600 supervised completion tokens. Compact
48x1, baseline 64x2 and wider 96x2 were kept within the measured short CPU envelope;
observed RSS stayed below 352 MiB and sampled CPU temperatures at or below 59°C.
Hard training monitor limits are 45 seconds, 650 MiB, two threads and at least
500 MiB available RAM. Balanced batching is compared against the unchanged
standard schedule at 64x2. Same-token exposure is not same compute: width changes
cost. No run was allowed a large or long training budget.

| Pilot | Parameters | Supervised tokens | Validation loss | Masked test PPL | Correct tool | JSON schema | Train s | RSS MiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
""" % (
    selected["validation"]["loss"],
    selected["test"]["loss"],
    selected["test"]["perplexity"],
)
text += (
    "\n".join(rows)
    + """

All checkpoints round-trip through safetensors exactly. Exact CPU seconds,
completion throughput, checkpoint save time/bytes, hashes and generation records
are in evidence/phase8/core-matrix.json. Weights/tokenizer/data remain under
`artifacts/tool-sft/phase8-*-40/`, not Git. Old format and selected checkpoint are
unchanged. Balanced ordering reduced validation loss but did not improve 64x2
tool accuracy and reduced JSON validity to 14/16. The wider pilot reached 6/16
correct tools, with 14/16 valid schema. This is a one-seed, tiny exploratory test,
not a reliable instruction-following or argument-generation capability. The
responses contain empty argument objects. No model was promoted.

## Dataset engineering

The existing licensed PSF expansion/deduplication/frozen evaluation pipeline is
preserved. A separate authored fixture corpus now covers general text, code,
instructions, tool calls, recovery and planning: 18 source records, 816 selected-
tokenizer tokens. Manifest records explicit CC0 provenance, normalized hashes,
source-level splits, quality/credential checks and zero exact five-word overlap
across splits. It is tiny pipeline evidence, not an adequate foundation corpus,
and was not mixed into this pilot matrix. Private conversations are excluded.

## Hardware extrapolation limits

FP32 Adam training requires roughly 16 bytes/parameter for weights, gradients
and two optimizer moments, before activations, framework memory or checkpoints:

| Size | Parameter/gradient/Adam state only | Status |
| --- | ---: | --- |
| 10M | 0.15 GiB | Future reviewed CPU experiment, needs better data and activation measurements |
| 100M | 1.49 GiB | Likely memory pressure alongside services; sustained GPU study recommended |
| 1B | 14.90 GiB | Exceeds this laptop before activations |

The wider toy run computes 20,320 padded sequence positions per training session
in about 1.12 seconds. A naive inverse-parameter extrapolation implies roughly
610 positions/s at 10M and 61 at 100M: 100M positions would take about 1.9 or 19
days respectively. These are optimistic arithmetic illustrations, **not measured
training schedules**: padded JSON batches, kernel efficiency, sustained thermals,
context, data loading and evaluation make them unsuitable for purchase/budget
commitments. Actual token throughput differs from padded positions and supervised
completion throughput. Next sizes need a short feasibility probe first.

Next: expand rights-reviewed diverse data and untouched task-family holdouts,
repeat multiple seeds, assess arguments and recovery on executable tasks, and
compare against an authorized stronger assistant backend. Then measure a 5–10M
research configuration; do not scale from a low repetitive-JSON perplexity alone.
GPU training additionally needs CUDA/mixed precision and optimizer/RNG recovery
validation. Reuse the existing hardware decision report; buy/provision nothing
without a new measured benchmark and owner decision.
"""
)
(ROOT / "docs/NEXORA_CORE_SCALING.md").write_text(text)
