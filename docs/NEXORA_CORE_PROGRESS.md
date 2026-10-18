# NEXORA Core progress — Phase 6

Full history: `docs/NEXORA_CORE_TRAINING.md` (Phase 4),
`docs/NEXORA_TRAINING_STRATEGY.md` and `docs/INSTRUCTION_TUNING.md`
(Phase 5). This page is the Phase 6 checkpoint on that progress.

## No new training this pass

Milestone F (model intelligence) in Phase 6's own execution order comes
after knowledge/retrieval, and this pass stopped at Milestone C (research
agent) per the "finish each vertical slice before expanding" instruction.
No new NEXORA Core training run happened in this pass. The selected
checkpoint is unchanged: `phase2-small-language`
(`artifacts/selected-model.json`), 984,192 parameters, test loss
4.1786 / perplexity 65.28, independently re-reproduced to 8 significant
figures as recently as `docs/phase5-system-audit.md`.

## Where things actually stand

- **Architecture**: reviewed in Phase 5, found to already follow current
  best practice (RoPE, RMSNorm, SwiGLU, SDPA); no change justified by
  evidence, none made.
- **Instruction-following**: one real pilot
  (`phase5-instruction-pilot-v1`) trained, evaluated on a clean held-out
  set, scored 0/6 -- memorization without generalization. Not promoted.
- **Tool use**: baseline measured (0/3 Core, 1/3 SmolLM2), not yet
  trained on; see `docs/TOOL_USE_TRAINING.md` for why and what's needed
  first.
- **Code generation / structured outputs**: measured in
  `docs/AGENT_EVALUATION.md` (0/2 structured JSON, 0/2 coding for Core);
  not separately trained on this pass.
- **Context length / long-context**: unchanged (64/128 tokens for
  tiny/small profiles); not identified as the actual bottleneck (data
  scale and loss masking are, per `docs/NEXORA_TRAINING_STRATEGY.md`).

## The one standing priority, repeated because it hasn't been done yet

`docs/NEXORA_TRAINING_STRATEGY.md`'s roadmap, written in Phase 5, named
completion-only loss masking as priority #1 for any future instruction or
tool-use training to produce a meaningfully different result. That
remains true and remains undone. Every Phase 6 section that depends on a
more capable NEXORA Core (tool-use training, instruction-following
improvements) is blocked on this same piece of training-loop engineering,
not on new data or new hardware.
