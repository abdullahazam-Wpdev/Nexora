# Hardware inspection — 2026-10-16

Inspected this machine using uname, lscpu, free, df, lsblk, lspci, command discovery, Python import discovery and /run/host/os-release. No private browser data or credentials accessed.

- Host: Fedora Linux 44 Workstation; kernel 7.2.9-201.fc44.x86_64.
- Execution environment: Freedesktop SDK 25.08 / Flatpak, not a full Fedora shell. Host package tools and services are not necessarily visible.
- CPU: Intel Core i5-1135G7, 4 cores / 8 threads, x86_64, AVX2.
- RAM: 7.5 GiB total, approximately 2.1 GiB available at inspection. 7.5 GiB zram swap, approximately 2.4 GiB already used. Recheck availability before training.
- GPU: Intel TigerLake-LP GT2 Iris Xe integrated graphics; /dev/dri present. No NVIDIA GPU, nvidia-smi, CUDA or ROCm tools detected. No dedicated VRAM established. Integrated graphics shares system RAM.
- Storage: 238.5 GiB SK hynix internal NVMe, 153 GiB free in the workspace filesystem. No external SSD/USB block device shown in lsblk.
- Initially available: Python 3.13.16, Git, curl, wget, lspci. Node/npm, Podman, torch, tokenizers, FastAPI, pytest were initially absent. ss unavailable; ports 8000 and 3000 were subsequently verified by successful binds.

## Initial configuration

CPU float32; 2 PyTorch threads; 2 transformer blocks; width 64; 4 heads; context 64; vocabulary 384; microbatch 4, accumulation 2. 143,808 parameters with the trained 289-token vocabulary (384 requested maximum). Random weights only. No GPU drivers or privileged packages installed. Keep training allocations below 500 MiB where practical and never interpret zram/external disks as additional physical RAM. API refuses new training below 500 MiB available memory; this is an entry check rather than a hard OS memory quota.

CPU is the verified acceleration path. Intel GPU acceleration is a future compatibility investigation, not enabled. CUDA cannot accelerate this Intel GPU.

## Upgrade triggers

No SSD upgrade is needed for this tiny milestone. Current RAM permits the smoke model; close memory-heavy applications before larger runs. Consider 16–32 GiB RAM if sustained swapping or dataset preprocessing exceeds available memory; verify laptop RAM upgradeability first. An external SSD becomes useful once artifacts exceed roughly 50 GiB or internal free space drops below 30 GiB. Large language pretraining needs a separately benchmarked GPU workstation, not just an SSD purchase.
