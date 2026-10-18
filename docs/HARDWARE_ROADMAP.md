# Hardware roadmap — current machine and future workstation

Authoritative, previously-verified reports:
[hardware-report.md](hardware-report.md),
[hardware-storage-upgrade-report.md](hardware-storage-upgrade-report.md),
[future-gpu-readiness.md](future-gpu-readiness.md),
[gpu-workstation-decision.md](gpu-workstation-decision.md). This page is the
Phase 4 pointer and re-verifies the numbers that matter for this pass's
NVIDIA work, since the Phase 4 prompt's assumed configuration does not match
the machine.

## Re-measured 2026-10-18 (this session)

| Item | Phase 4 prompt assumed | Actually measured this session |
| --- | --- | --- |
| RAM | 32 GB | **7.5 GiB total**; 181 MiB free / ~1 GiB available at the start of this session, 5+ GiB already in zram swap |
| Storage free | "more than 150 GB" | 184 GiB free on `/home` -- this one matches |
| GPU | not stated; prompt says "do not assume NVIDIA GPU acceleration exists" | Confirmed: Intel Iris Xe integrated graphics only; no `nvidia-smi`, no CUDA, no discrete GPU of any vendor |
| CPU | not stated | Intel Core i5-1135G7, 4 cores / 8 threads |

**The RAM figure in the Phase 4 prompt is wrong for this machine by roughly
4x.** Re-measured independently again in Phase 5
(`docs/phase5-system-audit.md`), via both a shell command and the running
API's own `psutil` check: same 7.5 GiB, three sessions in a row now. Every sizing/feasibility conclusion below uses the measured 7.5 GiB,
not the assumed 32 GiB. If you actually have a different, 32 GB machine in
mind for this work, tell me and I will redo this section against that
machine instead of this one.

## What this means for NVIDIA local deployment (Phase 4 §4)

- No NVIDIA GPU exists on this machine, so no NVIDIA local GPU-accelerated
  model (any NIM container, any CUDA-dependent download) can run here at
  all, regardless of RAM.
- CPU-only local inference of larger downloadable NVIDIA weights (e.g. the
  4B-parameter Nemotron GGUF staged by `scripts/download-nvidia-reference.py`)
  is infeasible for real use at 7.5 GiB total RAM: a Q4_K_M quantization of a
  4B model is ~2.8 GB on disk and needs comparable RAM just to map, on a
  machine that already runs with under 1 GiB free during normal use. It would
  thrash swap rather than serve usable inference. That script remains
  **unexecuted**; running it is a 2.8 GB download requiring your explicit
  approval, and loading the result for inference is not recommended on this
  hardware at all.
- Hosted NVIDIA NIM inference (this pass's new adapter, see
  [NVIDIA_NIM.md](NVIDIA_NIM.md)) is the correct path for anything beyond the
  existing pinned SmolLM2 135M local reference, consistent with Phase 4 §4's
  own instruction to prefer hosted inference for larger models.

## Future GPU workstation

Unchanged from [gpu-workstation-decision.md](gpu-workstation-decision.md) and
[future-gpu-readiness.md](future-gpu-readiness.md): no GPU has been purchased
or provisioned, and none should be without a benchmarked, costed decision.
The sizing table in `future-gpu-readiness.md` remains the right reference
once that purchase is actually being planned.
