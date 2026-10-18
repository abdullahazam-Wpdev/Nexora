# GPU / hardware scaling decision — Phase 5

Full prior analysis: `docs/future-gpu-readiness.md`,
`docs/gpu-workstation-decision.md`, `docs/HARDWARE_ROADMAP.md`. This page
adds this session's measured numbers and keeps the same conclusion: **no
GPU purchase is justified by what has actually been measured.**

## Measured throughput, this session

| Run | Parameters | Profile | Steps | Wall seconds | Train tokens/s |
| --- | ---: | --- | ---: | ---: | ---: |
| `phase2-small-language` (selected baseline) | 984,192 | small | 400 | 71.4 | 9,170 |
| `phase5-instruction-pilot-v1` (new) | 918,656 | small | 300 | 32.9 | ~9,340 |

Consistent with the prior phase's numbers (9,170-21,400 tokens/s depending
on profile) on the same CPU (Intel i5-1135G7, 4C/8T). This confirms CPU
training throughput for the `small` profile is stable and reproducible
across sessions, not a one-off measurement.

## Current practical limits, re-confirmed

- **RAM**: 7.5 GiB total, ~1 GiB typically available (see
  `docs/phase5-system-audit.md`) -- not the 32 GiB originally assumed.
- **Practical parameter ceiling today**: sub-2M parameters trains
  comfortably in well under a minute for a few hundred steps. The existing
  `docs/future-gpu-readiness.md` sizing calculator
  (`python -m nexora.scaling`) estimates tens-of-millions-of-parameters
  configurations need a 12-16 GB CUDA GPU and 32 GB host RAM to be
  feasible at all -- this machine has neither.
- **Practical token budget today**: a few hundred thousand training tokens
  per run completes in under two minutes; this pass's `max_seconds=170`
  safety cap was never hit (the run finished in 33s). Scaling to the
  millions-of-tokens range that would be needed for real instruction
  generalization (see `docs/INSTRUCTION_TUNING.md`) is a data-engineering
  and time problem, not strictly a hardware-blocked one at this parameter
  count -- it is feasible on this CPU if a larger approved corpus existed.
- **GPU**: none present (Intel Iris Xe integrated only). CUDA cannot
  accelerate it. No change from prior phases.

## Upgrade triggers (unchanged from `future-gpu-readiness.md`, restated)

| Trigger | Action |
| --- | --- |
| Sustained swapping during normal (non-training) use | Consider a RAM upgrade first -- cheaper and addresses the actual current pain point (this session observed 5-6 GiB of swap in use just running the API, tests and an unrelated background download) |
| A specific tens-of-millions-of-parameters experiment is designed and its FLOP/memory estimate is computed via `nexora.scaling` | Benchmark a rented or borrowed GPU on that exact workload before buying anything |
| Internal free storage drops below ~30 GiB | External SSD, not before |

## Checkpoint backup strategy

Unchanged: checkpoints live under `artifacts/runs/<id>/checkpoints/`,
sha256-pinned and verified on every load (`verify_checkpoint`). No
off-machine backup is configured. At current scale (sub-1M-parameter
checkpoints, each well under 10 MB) this is low-risk; it becomes worth
automating once a run's checkpoint size or training wall-time makes
re-running from scratch costly -- neither is true yet.

## Decision

Do not recommend or purchase GPU hardware this pass. Nothing measured this
session changes the prior phase's conclusion. The actual next bottleneck,
per `docs/NEXORA_TRAINING_STRATEGY.md`, is approved data diversity and a
loss-masking implementation -- both software/data work that does not
require new hardware.
