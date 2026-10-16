# Architecture and shared contracts

This is a local research bootstrap, not the entire proposed AI ecosystem.

- `nexora/model.py`: independent PyTorch Core architecture.
- `nexora/datasets.py`: approval gate, normalized text, exact deduplication, hashes, basic sensitive-data rejection and deterministic document splits.
- `nexora/train.py`: arithmetic data fixture, tokenizer training, contiguous token packing, CPU optimizer loop, train/validation/test loss, safe tensor inference weights and local optimizer resume state.
- `nexora/api.py`: FastAPI control plane, SQLite project/memory/audit persistence, dataset API, subprocess training control, local inference, health, integration registry.
- `frontend/`: Next.js App Router / TypeScript dashboard. Same-origin rewrites connect to the API. All visible counters and plots come from APIs; future modules are labeled planned.
- `artifacts/`: configurable non-Git research storage. `NEXORA_STORAGE` must be consistent across CLI and server. Public inference only loads safetensors; optimizer resume uses weights_only=True on locally created state.

## Shared interfaces

API schema: GET http://127.0.0.1:8000/openapi.json. Each record has a stable id. Project `local` and actor `local-owner` are bootstrap defaults. All mutation audit entries contain actor, action, detail and timestamp. Training has at most one process launched per running API instance; CLI and multiple API instances are not coordinated. Use one API worker.

Identity is localhost ownership, not production authentication. Browser mutations reject foreign Origins. There are no enabled terminal/browser tools, public listeners, credential integrations or arbitrary command-execution endpoints. Local malicious processes remain outside this bootstrap's protection boundary. Do not deploy publicly.

Datasets require explicit approved=true, an allowlisted license identifier and provenance. This records the operator's assertion; it cannot verify actual ownership or legal validity. Detection uses conservative patterns and is not comprehensive DLP. Full license review, semantic quality checks, source discovery and retention policy remain future work. POST ingestion stores documents in SQLite; the initial trainer deliberately trains only on its reproducible arithmetic fixture, not arbitrary submitted datasets.

## Module roadmap interfaces

One: project memory and local inference are groundwork; conversational/research/voice interfaces pending.
Code: future scoped repository tools returning diffs, exit codes and test evidence; permission checks required before execution.
Business: future authenticated provider adapters; no credentials or paid APIs configured.
Shield: future scope-bound authorized assessment jobs; no security scanners enabled.
Creative: future media jobs with source/license/artifact metadata; no generation model configured.
Workforce: future durable jobs with role, permissions, approvals, event stream and audit references.
Virtual Office: future renderer of actual workforce events; no simulated activity.
Evolution Lab: current reproducible training run; candidate comparison and controlled promotion pending.
Proof-of-Work: pytest and browser evidence are current foundations; signed completion records/approval UI pending.

PostgreSQL and Redis are provided as optional Compose configuration only. SQLite is the actual operational database. Migrations are SQLite-specific; PostgreSQL adapter and migrations must be implemented before switching. No distributed training, authentication, autonomous self-improvement or frontier intelligence is claimed.
