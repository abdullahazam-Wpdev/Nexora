# GPU workstation purchase decision — Phase 3

**Decision: do not purchase yet.** Complete matched-budget/data-quality research and establish an executable GPU acceptance benchmark first. The delivered experiments are CPU-only, and no GPU throughput has been measured. A GPU would accelerate training; it would not supply a licensed corpus, instruction tuning or demonstrated assistant capability.

This report compares resource envelopes, not current retailer prices or guaranteed performance. No budget, local quote, exact chassis/CPU or electricity cost was supplied; a defensible total-cost quote remains open. Nothing was purchased, provisioned or installed system-wide.

## GPU choices and capacity trade-offs

| Candidate | VRAM | Reference board power | NVIDIA reference minimum system PSU | Purchase implication |
| --- | ---: | ---: | ---: | --- |
| RTX 5070 Ti | 16 GB | 300 W | 750 W | Entry research option for tens to low hundreds of millions of parameters if measured activation/batch budget fits |
| RTX 5080 | 16 GB | 360 W | 850 W | Same memory ceiling as 5070 Ti; justify any extra cost with this trainer's measured tokens/s, not gaming charts |
| RTX 3090 (existing/used-market option) | 24 GB | 350 W | 750 W | More memory headroom than 16 GB cards; compare exact card condition, memory temperature, warranty and tested throughput before any used purchase |
| RTX 4090 | 24 GB | 450 W | 850 W | Same capacity class as 3090, different compute/power; no speedup for this code is claimed without a benchmark |
| RTX 5090 | 32 GB | 575 W | 1000 W | Extra memory for larger batches/context or optimizer state; higher power/cooling/UPS envelope |
| RTX PRO 6000 Blackwell Workstation | 96 GB ECC | 600 W | Complete-system integrator sizing required | Capacity-oriented professional option; current sub-3M-parameter work does not justify it |

Primary manufacturer sources: [5070 family](https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5070-family/), [5080](https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5080/), [3090 reference series](https://www.nvidia.com/en-us/geforce/graphics-cards/30-series/), [4090](https://www.nvidia.com/en-au/geforce/graphics-cards/40-series/rtx-4090/), [5090](https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/), [RTX PRO 6000](https://www.nvidia.com/en-us/products/workstations/professional-desktop-gpus/rtx-pro-6000/). These are reference designs, not guarantees for partner cards or a high-power CPU build. Specifications checked during this cycle; prices/availability were not assumed.

VRAM capacity does not indicate trained model quality. A single GPU must fit model, gradients, Adam moments, activations and workspaces. FP32 weights/gradients/Adam moments alone require approximately 16 bytes/parameter: 100M ≈1.49 GiB, 1B ≈14.90 GiB, 7B ≈104.31 GiB before activations. Mixed precision does not automatically remove FP32 optimizer state. Full 7B AdamW pretraining does not fit a 24/32 GB card; quantized inference or parameter-efficient fine-tuning is a different workload. DDP duplicates state per GPU; memory sharding would be separate implementation work.

## Whole workstation envelopes (planning, not a parts purchase list)

| Research target | System RAM | Working NVMe | Cooling/PSU/UPS planning |
| --- | --- | --- | --- |
| 10–100M independent model research | 32 GB workable; 64 GB preferred for preprocessing and headroom | 1 TB minimum planning pool; 2 TB convenient with retained data/checkpoints | Measure actual load; reference GPU PSU minimum is a floor, not a complete build validation |
| Hundreds of millions / longer context | 64–128 GB, based on CPU staging and dataset processing | 2 TB+ scratch plus physically separate backup | Match exact board dimensions, airflow, connectors and sustained CPU/GPU heat; qualify an ATX PSU with the chosen builder |
| ~1B full pretraining | 128 GB+ may be appropriate; not a guarantee of VRAM fit | Multiple TB according to token and checkpoint retention plan | Dataset, duration, power and recovery plan become major constraints; obtain measured workload sizing before committing |

An 850 W-class PSU may be a useful starting envelope for a 300–450 W GPU build with a moderate CPU, but must meet the exact manufacturer's requirements and connector specification. A 575 W reference GPU requires at least NVIDIA's stated 1000 W system supply; high-power CPUs or partner cards may require more. The 600 W professional card should be sized as a complete system by its integrator. Do not select wattage solely from GPU TDP, or assume PSU efficiency certification proves transient response/quality.

Cooling must sustain both CPU and GPU dissipation under continuous training, including memory modules and storage; validate fan behavior, board clearance and temperatures over a sustained acceptance run. Do not infer sustained cooling from this laptop's short CPU experiments. No kernel/driver or chassis modification is proposed for the current laptop.

UPS selection must satisfy **both continuous watts and VA**, local mains compatibility, active-PFC compatibility and manufacturer runtime curves at measured load. Prefer a compatible sine-wave output where required. For illustration, a measured 650 W workstation needs more than 650 W continuous UPS capacity plus operating margin; a 1500 VA label alone does not establish sufficient watts or runtime. Five-to-ten-minute checkpoint/shutdown runtime should be checked against the selected UPS battery chart with aging margin, not inferred from VA. See the [APC UPS buying guide](https://www.apc.com/us/en/support/product-support/ups-buying-guide-for-selecting-a-battery-backup-system.jsp). No wiring or electrical installation is authorized.

## Compute needs, not marketing TOPS

A rough dense autoregressive pretraining estimate is **6 × parameters × training tokens FLOPs**, excluding overhead. Example scenarios below use 20 tokens/parameter only as a planning scenario; it is not a universal data optimum or success threshold. The 6PT approximation and compute/data trade-offs are discussed in [compute-optimal model research](https://arxiv.org/abs/2203.15556).

| Scenario | Training tokens | Approximate compute | At assumed sustained 10 / 30 / 60 TFLOP/s |
| --- | ---: | ---: | --- |
| 100M parameters | 2B | 1.2×10^18 FLOPs | 33.3 h / 11.1 h / 5.6 h |
| 1B parameters | 20B | 1.2×10^20 FLOPs | 138.9 d / 46.3 d / 23.1 d |

These are **hypothetical sustained compute rates**, not measured estimates for any named GPU. They exclude evaluation, failed runs, data/optimizer/checkpoint overhead and tuning repeats. Gaming FPS, FP4 AI TOPS and peak tensor-core marketing figures must not be substituted for sustained BF16/FP32 training throughput. No such long job is approved or launched.

## Before a purchase decision

1. Fix the model/data/tokenizer/context/batch target and rights-approved token budget.
2. On candidate hardware, run the same correctness/resume tests and a short representative forward/backward/evaluation workload; measure peak allocated/reserved VRAM, tokens/s, wall power, temperature and checkpoint latency. A seller/integrator can provide this acceptance evidence without granting us paid/cloud access.
3. Confirm PyTorch/CUDA/driver support for the exact GPU, host OS and desired precision; this repository currently installs CPU PyTorch, and GPU/AMP/DDP execution remains unimplemented.
4. Compare local complete-system quotations and warranty against **measured usable VRAM and tokens per unit cost/energy**. Obtain explicit owner approval for any purchase, paid rental, driver install or long-running job.
5. Include separate backup storage and restore drills. No amount of VRAM replaces checkpoint integrity, independent evaluation or data provenance.
