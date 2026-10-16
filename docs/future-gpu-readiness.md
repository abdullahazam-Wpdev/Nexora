# Future GPU readiness and sizing

No NVIDIA GPU is present, no driver/CUDA install was attempted, and no cloud machine was provisioned. The verified trainer is **CPU float32**. GPU/DDP/AMP readiness below is a design and sizing plan, not an executed GPU implementation.

`python -m nexora.scaling` is a working allocation-free sizing calculator. It reports current-architecture parameter counts, a lower bound of 16 bytes/parameter for FP32 weights+gradients+Adam moments, and a rough 6×parameters×training-tokens FLOP estimate. It excludes activations, allocator workspaces, optimizer intermediates, attention memory and communication; do not buy hardware using the lower bound alone. The common training-compute approximation is discussed in [compute-optimal language model research](https://arxiv.org/abs/2203.15556). A 20 tokens/parameter target is an illustrative research scenario, not a universal optimum or quality guarantee.

Prepared sizing candidates are in `docs/evidence/phase2/future-sizing.json`: Medium is width 512, 8 blocks, context 512, vocabulary 8192; Large is width 1024, 24 blocks, context 2048, vocabulary 32000. These are future experiment candidates, not current trained products. The CPU API only allows Tiny/Small and caps its configurations.

## Migration design

1. Copy source, exact dependency locks, dataset manifests/raw notices, token shards and complete checkpoint folders. Verify hashes, run CPU tests, establish GPU throughput/peak memory on a tiny smoke workload first.
2. For one NVIDIA GPU: choose compatible hardware/driver using [NVIDIA's CUDA installation guide](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/), with explicit owner approval before driver changes. Add device transfer to mapped batches/model, torch.amp autocast, and a GradScaler for FP16; prefer BF16 only after hardware support and numerical checks. Preserve CPU fallback. Current resume state is CPU-only; CUDA RNG/scaler state must be added before claiming exact GPU resume.
3. Add activation checkpointing with PyTorch's non-reentrant API and test gradient equivalence before increasing depth/context. Consider bounded pinned-memory staging only if measured beneficial; do not assume mmap means unlimited RAM.
4. Multi-GPU: launch with torchrun, DistributedDataParallel, rank-local device selection, deterministic DistributedSampler epochs and rank-aware RNG states. DDP duplicates optimizer/model memory on each GPU; it does **not** pool VRAM. Rank 0 publishes checkpoints and metrics only after coordinated barriers. Handle cancellation on all ranks. FSDP/ZeRO or tensor parallelism would be separate work for models that do not fit one GPU.
5. Streaming: current shards are memory-mapped local arrays. Future remote streaming must pin source versions, shard order, sampler cursor and worker RNG in checkpoints. Stage object storage on local NVMe and verify before use. Object storage/NAS adapters are not implemented.
6. Long-running jobs need supervisor recovery, periodic atomic checkpoints, verified restore drills and off-machine backups. Current API workers survive API restarts and can resume last published checkpoints, but there is no automatic crash restart or multi-host queue.

Primary references: [PyTorch AMP](https://docs.pytorch.org/docs/2.14/amp.html), [distributed training](https://docs.pytorch.org/docs/2.14/distributed.html), and [reproducibility](https://docs.pytorch.org/docs/2.14/notes/randomness.html).

## Hardware sizing guidance

| Training scale | Planning envelope; must benchmark before purchase |
| --- | --- |
| Existing Tiny/Small CPU | Current RAM supports the measured bounded experiments; more RAM improves headroom but does not create GPU compute |
| Tens of millions of parameters | Start feasibility work on a 12–16 GB CUDA GPU and 32 GB host RAM; context/batch/optimizer can require more VRAM |
| Hundreds of millions | Investigate 24 GB+ GPU memory and 64 GB+ host RAM; use measured activation budget and checkpoint retention, not parameter weights alone |
| ~1 billion with FP32 AdamW | ~16 GB optimizer/model state lower bound before activations; 24–48 GB+ GPU or memory-sharded design may be needed |
| Multi-billion | New compute/data/parallelism project; DDP alone cannot combine GPU memory |

Provision enough internal NVMe for immutable raw/processed data, temporary shards, multiple optimizer checkpoints and backups; 1–2 TB is a planning starting point for a future workstation, not a current laptop requirement. A model checkpoint alone is roughly 4P bytes of FP32 weights; optimizer/resume state can be much larger, and retained steps multiply capacity needs.

Cooling must sustain measured CPU/GPU board power; laptop short-run results do not establish workstation throughput. PSU capacity must follow the chosen GPU/CPU manufacturer's board and transient-power specifications with appropriate connectors; no fixed wattage is defensible before part selection. Match UPS watts/VA and runtime to the measured system load and graceful checkpoint/shutdown needs. Use independent backup media. Ethernet requirements follow dataset/checkpoint transfer and cluster communication; multi-GPU/multi-node bandwidth must be benchmarked rather than assumed from nominal link speed.

Larger training requires compute throughput, VRAM bandwidth/capacity, reliable power/cooling, clean data and validation—not only more system RAM. Dollar cost and multi-hour training remain unapproved; no purchases or cloud resources are required for this delivered milestone.
