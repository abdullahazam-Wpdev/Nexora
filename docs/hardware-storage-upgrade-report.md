# Hardware, storage and upgrade audit — 2026-10-16

## Measured environment

DMI identifies **HP EliteBook 830 G8 Notebook PC** (product version SBKPFV3). Fedora 44 Workstation, kernel 7.2.9-201.fc44.x86_64; tools execute in the Freedesktop Flatpak SDK. Intel i5-1135G7, 4 cores/8 threads, integrated Tiger Lake Iris Xe-class GPU. No NVIDIA GPU or dedicated VRAM established. No CUDA driver changes made.

RAM: 8,030,441,472 bytes (7.48 GiB); available 1,563,471,872 bytes (1.46 GiB) at audit. Zram swap: 7.48 GiB total, 3.13 GiB in use. CPU package 54°C at audit, NVMe composite 31.85°C. Battery approximately 71%, **not plugged in**; frequency/power behavior may vary. Short experiments use two CPU threads and abort above an 88°C CPU reading. Sensor access is available; this is monitored, not a guarantee against sudden thermal events or OS OOM.

Internal SK hynix NVMe: 238.5 GiB physical; workspace filesystem 253,282,484,224 bytes, free 161,371,344,896 bytes (150.29 GiB) at reinspection. Previous report rounded free space to 153 GiB; current measurement is about 2.7 GiB lower. The original report did not retain an exact pre-install disk snapshot, so the difference cannot be attributed precisely to cleanup/dependencies. No external block drive found. Free space is sufficient; **an external SSD is not required now**.

Evidence: `docs/evidence/phase2/hardware.json`. Throughput and peak RSS are recorded per actual experiment in `experiment-matrix.json`; these short runs do not establish sustained plugged-in speed.

## RAM compatibility

HP-authored QuickSpecs **c06969200, version 15**, for this exact model states DDR4-3200 memory up to 64 GB, two accessible/upgradeable SO-DIMM slots and dual-channel support. The accessible PDF is an [HP QuickSpecs mirror](https://hp.it-shop.bg/uploaded/8/8/EliteBook-830-G8-QS.pdf). HP's own [BIOS guide](https://h10032.www1.hp.com/ctg/Manual/c07496764.pdf) shows the model with two bottom memory slots. HP also lists compatible [16 GB DDR4-3200 memory](https://support.hp.com/us-en/product/setup-user-guides/hp-16-gb-3200mhz-ddr4-memory-series/model/2100181940) and [32 GB DDR4-3200 modules](https://support.hp.com/in-en/product/setup-user-guides/hp-32-gb-3200mhz-ddr4-memory/model/2100907559).

This supports replaceable **DDR4-3200 SO-DIMMs**, not DDR5 or soldered-only RAM, at the model level. Current slot population, actual installed module speed/part number and current channel mode remain **unverified**: unprivileged dmidecode cannot read SMBIOS tables or /dev/mem. No privileged inspection was attempted. The PCI graphics label does not prove dual-channel RAM.

Supported capacity plans: 16 GB = 2×8 GB; 32 GB = 2×16 GB; 64 GB = 2×32 GB, matched DDR4-3200 SO-DIMMs. For this workload 32 GB is the practical next target, with 16 GB an interim improvement; 64 GB is supported by the platform documentation but does not turn this CPU laptop into a large-model training workstation. Confirm current slot population in BIOS or through a technician before selecting modules. No purchase or guarantee of a particular retail SKU is made.

## Cleanup inspection (no important data deleted)

Measured project usage before new experiments: `.venv` ~1.2 GiB (active; retain), `.tools` ~199 MiB (active Node; retain), `frontend/node_modules` ~534 MiB (rebuildable but used), `frontend/.next` ~75 MiB (rebuildable but active production server uses it), original `artifacts` ~2.3 MiB (research evidence; retain). Source/lock files are retained. Only one project virtual environment exists. No external package caches or personal files were deleted or traversed for cleanup.

Potential recoverable space: ~75 MiB from `.next` after stopping the UI, or ~534 MiB from node_modules if frontend development is paused. Neither was removed because both support the running application. Old logs are small; model artifacts are referenced research evidence. No material safe cleanup benefit justifies disrupting services. Container image/volume storage was newly created for verified local services and is retained. Browser cache outside the project was not removed.

## Storage layout

Keep source and Python environment on internal NVMe. Set `NEXORA_STORAGE=/absolute/path` for raw source snapshots (`raw/`), immutable prepared datasets (`datasets/`), run-local mapped token shards (`runs/<id>/*.npy`), tokenizer/checkpoint bundles (`runs/<id>/checkpoints/`), job logs and legacy artifacts. Default is project `artifacts/`; all large/generated training data are excluded from Git. Keep backups on another physical device; copy while writers are stopped and preserve SHA-256 manifests.

A future 1 TB SSD is reasonable once retained datasets/checkpoints exceed ~50 GiB or internal free space approaches 30 GiB; 2 TB is justified by a measured retention plan, not by current needs. USB/NAS capacity never increases RAM. Local mapped-shard random reads prefer NVMe/SSD; test NAS locking and throughput before using it for concurrent jobs. Object storage needs a staging adapter and is not currently implemented.
