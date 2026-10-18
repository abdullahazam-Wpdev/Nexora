# NEXORA Core training strategy — Phase 5

## Architecture review (Phase C) -- what was actually inspected

Read in full this pass: `nexora/model.py` (architecture), `nexora/research.py`
(training loop, optimizer, schedule, checkpointing). Checklist and finding
for each item the Phase 5 prompt asked to evaluate:

| Item | Current implementation | Assessment |
| --- | --- | --- |
| Tokenizer | Byte-level BPE (`tokenizers` library), trained fresh per dataset | Reasonable for this scale; Unicode round-trip tested (Latin accents, Greek, Urdu, Japanese, emoji) |
| Context length | 64 (tiny) / 128 (small) | Small but matches the tiny training corpora; not yet a bottleneck versus data scale |
| Attention | `F.scaled_dot_product_attention` with RoPE, causal mask | Modern, flash-attention-eligible, correctly causal |
| Normalization | RMSNorm (pre-norm, two per block) | Matches current best practice (cheaper than LayerNorm, no bias term) |
| Positional embeddings | Rotary (RoPE), not learned/absolute | Correct modern choice; generalizes better to unseen lengths than learned absolute embeddings |
| Feed-forward | SwiGLU (`gate`/`up`/`down`, SiLU activation) | Matches current best practice over a plain ReLU MLP |
| Initialization | Normal(0, init_std), with GPT-2-style `1/sqrt(2*layers)` scaling on attention-output and down-projection weights | Standard, correct residual-stream variance control |
| Optimizer | AdamW, weight decay applied only to `ndim >= 2` tensors (matrices, not norms/biases) | Standard, correct |
| LR schedule | Linear warmup + cosine decay | Standard, correct |
| Gradient accumulation | Implemented (`accumulation` steps averaged before `optimizer.step()`) | Present and tested |
| Gradient clipping | `clip_grad_norm_`, norm recorded per step | Present and tested |
| Checkpoint compatibility | sha256-pinned tensors, strict `load_state_dict`, finite-value check, tied-embedding equality check | Thorough; independently re-verified this session (see `docs/phase5-system-audit.md`) |
| Dataset packing | Contiguous tokens with an `[EOS]` between documents, source-level fixed splits | Simple and correct; no cross-document attention leakage since each window is a flat slice, not masked per-document (acceptable at this context length) |
| Training efficiency | ~9,000-21,000 train tokens/s depending on config, measured and recorded per run | Already measured, not asserted |
| Validation methodology | Full held-out split evaluated every `eval_every` steps, token-weighted loss, no RNG consumption, remainder batches included | Rigorous for the scale |

**Conclusion: no architecture change is justified by evidence.** The
architecture already follows current best practice for a model this size
(RoPE, RMSNorm, SwiGLU, SDPA, proper init scaling) -- changing it now would
not be evidence-driven, it would be churn. The actual bottlenecks,
confirmed by this pass's own experiment (`docs/INSTRUCTION_TUNING.md`), are:

1. **Data scale and diversity.** 48-61 document pilots and a ~400K-token
   single-domain pretraining corpus are far below what any published small-
   model research uses to demonstrate instruction-following or arithmetic
   generalization.
2. **No completion-only loss masking** for instruction data -- see
   `docs/INSTRUCTION_TUNING.md` §"What would need to change."
3. **Parameter count.** 918K-984K parameters is below where generalization
   for these tasks reliably emerges, independent of data quality.

None of these are architecture problems; all three point at data and
training-objective work, which is where the next real session's effort
should go, not at redesigning `nexora/model.py`.

## Versioned configurations (unchanged)

`PROFILES = {"tiny": dim=64/layers=2/heads=4/context=64, "small":
dim=128/layers=4/heads=4/context=128}` in `nexora/research.py` remain the
two supported, hardware-feasible configurations. This pass added no new
profile -- the instruction pilot reused `small` for an apples-to-apples
architecture comparison against the selected baseline.

## What this pass changed and did not change

- Added: `artifacts/datasets/instruction-pilot-v1` (new dataset, Phase D),
  the `phase5-instruction-pilot-v1` training run (Phase F/G pilot), and
  `scripts/agent_eval.py` (Phase B harness).
- **Did not change**: `nexora/model.py`, `nexora/research.py`'s training
  loop (no loss masking added), or `artifacts/selected-model.json` (still
  `phase2-small-language`). No existing checkpoint, dataset, or test was
  modified or deleted.

## Roadmap for the next session, in priority order

1. Implement completion-only loss masking in the training loop -- the
   single highest-leverage change for any future instruction-tuning
   attempt to mean something.
2. Expand the instruction pilot to dozens of varied phrasings per pattern
   (not 6-8), written independently of any eval harness to avoid the
   contamination this pass caught and documented.
3. Re-run the pilot with masking + expanded data, and score it against a
   held-out set that was never touched during dataset authoring.
4. Only then consider whether a larger `PROFILES` entry is justified by a
   measured plateau, not assumed.
