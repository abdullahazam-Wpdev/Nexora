# NEXORA AI OS

Working local independent-model research platform: PyTorch foundation-model architecture, approved/versioned datasets, bounded experiment workers, full held-out evaluation, verified checkpoints and FastAPI control plane. The existing Next.js dashboard remains the local inspection/playground UI. No commercial model API or pretrained weights are required.

**Current models are small research language models, not reliable conversational assistants or coding agents.** See the [measured model comparison](docs/model-evaluation-report.md).

## Run

```sh
./scripts/start.sh
```

Dashboard: http://127.0.0.1:3000 · Interactive API: http://127.0.0.1:8000/docs

Use one API worker per workspace. Model training workers survive API restarts; stop them cooperatively through the cancellation endpoint before moving storage. Default network listeners bind localhost only. Identity/authentication is still local ownership, not production multi-user access control.

## Reproduce setup

```sh
./scripts/bootstrap.sh
```

Requires Python 3.11+ and Node 22+ (a verified project-local Node already exists in `.tools/node`). CPU PyTorch is pinned in `requirements.lock` along with installed tools. Source data/checkpoints/environments are excluded from Git.

## Acquire reviewed data and train

```sh
.venv/bin/python -m nexora.data_engine --catalog configs/python-tutorial.sources.json --approve-download
# Use the returned dataset ID in the next command:
.venv/bin/python -m nexora.research create --dataset DATASET_ID --profile small --steps 200 --run
.venv/bin/python -m nexora.research train RUN_ID --resume --steps 100
.venv/bin/python -m nexora.research infer RUN_ID 'Python is' --tokens 32
```

The provided source catalog is a small version-pinned human-authored CPython tutorial corpus under PSF-2.0. It retains full notices and pins every downloaded file's hash; total downloads are limited to 700 kB. No AI-generated prose, pretrained weights, credentials or paid service is used for research training. Never approve a new source merely because a manifest claims a license.

Working API flow:

- POST `/api/research/datasets`: explicitly approve documents with source groups, license, provenance and reviewer.
- GET `/api/research/datasets`: inspect IDs/versions and quality reports.
- POST `/api/research/runs`: choose dataset ID/profile/training limits and start a real worker.
- GET `/api/research/runs/{id}`: durable progress/errors after server restarts.
- POST `/api/research/runs/{id}/resume`, `/cancel`, `/generate`, `/select`.
- GET `/api/research/runs/{id}/checkpoint`: verify tensors/hashes.

`/select` makes the chosen checkpoint serve the existing playground's `/api/generate`. Existing training buttons now launch versioned research jobs and preserve the original arithmetic checkpoint. Old `/api/datasets` remains a compatibility endpoint; use `/api/research/datasets` to prepare selectable training data.

## Verify

```sh
./scripts/test.sh
.venv/bin/ruff check nexora tests scripts --select F
.venv/bin/python -m pip_audit
.venv/bin/python scripts/browser_qa.py
# With the approved Python dataset present; isolated real worker lifecycle QA:
.venv/bin/python -m scripts.research_qa
```

`python -m scripts.experiment_matrix` runs four bounded sequential experiments (120 seconds maximum per run). Named runs cannot be overwritten; choose new IDs for a new matrix or inspect retained results. `scripts/verify_baseline.py` is the historical baseline-audit runner and is not a generic current matrix test.

## Local infrastructure

```sh
.venv/bin/python scripts/infra.py up
.venv/bin/python scripts/infra.py verify
```

Rootless Podman is installed on the Fedora host and accessed through `scripts/host-podman.sh`; Compose is installed only in `.venv`. PostgreSQL/Redis were health- and persistence-tested. The application currently uses SQLite; PostgreSQL/Redis adapters remain future work. Passwords stay in ignored `.secrets/` and are mounted read-only with SELinux labeling. No password is passed in a command argument or committed.

## Storage and migration

Set `NEXORA_STORAGE=/absolute/path` consistently for server/CLI. Default: `artifacts/`. Layout: raw snapshots, immutable dataset versions, mapped run-local token shards, per-step checkpoint bundles and durable job records. Stop all writers before copying. Copy complete bundles with tokenizer, manifests and optimizer state; verify hashes on the destination. Recreate environments from locks; do not copy virtual environments across systems. CPU is verified; CUDA/DDP/AMP implementation and cross-device resume remain planned.

[Previous-work audit](docs/phase-1-audit.md) · [Hardware/RAM/storage](docs/hardware-storage-upgrade-report.md) · [Dataset strategy](docs/dataset-strategy.md) · [Model evaluation](docs/model-evaluation-report.md) · [GPU readiness](docs/future-gpu-readiness.md) · [Roadmap](docs/roadmap.md)
