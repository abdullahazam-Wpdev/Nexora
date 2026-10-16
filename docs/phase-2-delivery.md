# Phase 1.5 / Phase 2 delivery — 2026-10-16

## Verified outcome

NEXORA now has real versioned language datasets, unique bounded training jobs, full held-out evaluation, independently trained language checkpoints, per-run generation and durable API control. It does not yet provide reliable conversational assistance, reasoning or coding. No paid model API or pretrained weights supply its generation.

Original commit `6d3b60f` was reverified before changes. See [audit](phase-1-audit.md). Current code is on `research/phase2-model-reliability`; this cycle's commit is recorded in Git history. Run records include the pre-change parent Git commit, a dirty-tree flag and exact hashes of training implementation files, because experiments were executed before the final delivery commit.

## Final executed verification

Exact commands, outputs, exit statuses and durations: `docs/evidence/phase2/final/summary.json`.

| Check | Actual result |
| --- | --- |
| `.venv/bin/python -m pytest -q` | 19 passed |
| Ruff correctness checks (`--select F`) | Exit 0 |
| TypeScript | Exit 0 |
| Next.js production build | Exit 0 |
| npm vulnerability audit | Exit 0, no reported vulnerabilities |
| pip dependency consistency | Exit 0 |
| pip-audit | No known findings after local setuptools upgrade; CPU torch wheel skipped by service |
| Separate upstream `torch==2.14.1` advisory query | No known findings; not a binary audit of the CPU wheel |
| Real browser QA | 9 sections, 2 themes, 1440/390 px, local generation, no runtime errors or horizontal overflow |
| Real API worker QA | Launch/concurrent-job rejection, API-restart survival, resume 6→8, verified generation/selection and cancellation |
| Rootless container QA | PostgreSQL/Redis healthy, SQL/key persistence across restart, localhost ports verified |

API lifecycle evidence: `api-e2e.json`. Full final browser screenshots are retained under `final/browser/`. Model results and independent hash/tensor/roundtrip/contamination checks are in `experiment-matrix.json` and `independent-evaluation.json`.

## Actual training

Four CPU runs completed under 120-second wall, 900 MiB process RSS, 500 MiB available-RAM floor and 88°C CPU limits:

- 172,352-parameter Tiny benchmark: 20 steps, validation loss 6.4035.
- 172,352-parameter Tiny language: 400 steps, 204,800 training tokens, validation loss 4.7333, perplexity 113.67.
- **984,192-parameter Small language**: 400 steps, 409,600 training tokens, validation loss **4.4033**, validation perplexity **81.72**, test loss **4.1786**, test perplexity **65.28**.
- Same Small with lower learning rate: 400 steps, validation loss 4.4445, perplexity 85.16.

Small language was selected by validation loss for the playground API. Its training-only throughput was ~9,170 tokens/s, total wall time 71.38 seconds, peak RSS 396.6 MiB and max observed CPU temperature 71°C. These are short-run CPU observations on a partly loaded battery-powered laptop, not sustained workstation benchmarks. Tiny vs Small consumed different token budgets; do not treat this as a controlled model-size causal claim.

The old arithmetic runner was separately benchmarked for 20 steps under an isolated artifact root: 5,981 end-to-end tokens/s including tokenizer/eval/save time. Its original 170-step checkpoint was preserved; SHA-256 remains `e3c466eb5cff384cda66a94f92269f56d269de37e4fe8c6c2cc0d00ae02630ef`.

A real selected-model sample begins `Python is` and continues with misspelled fragments (full output: `selected-model-generation.json`). This exposes its present limitations rather than claiming useful assistant performance.

## Data

263,879 downloaded bytes; pinned CPython v3.13.0 tutorial plus complete license stack. 835 accepted source-traceable chunks; 642/48/145 train/validation/test; no exact document/source overlap. One shared 12-word shingle across train/test is recorded, with maximum document Jaccard 0.0263. Stronger source diversity and an untouched final test set are needed before further tuning.

## Repairs and issues encountered

- Replaced destructive single-run API training with unique research runs; protected old direct runner against fresh overwrite and coordinated it with the global lock.
- Added exact-resume tests and restored optimizer/sampler/scheduler identity. Original single sampled validation was insufficient for that claim.
- Added real dataset selection, full held-out evaluation, corruption checks and resource guards.
- Fixed resume-launch concurrency window and untrusted Host handling.
- Initial new numerical test fixtures were rejected by the intended alphabetic-quality filter; revised the fixture's deterministic representation. Retained initial failure evidence.
- pip audit found advisories in setuptools 78.1.0. Upgraded the project environment to 84.0.0 and repeated audits; no known findings remain in auditable packages. Initial report of four entries included advisory duplicates; do not describe them as four unique vulnerabilities.
- Found host Podman through the existing authorized Flatpak host bridge. Initial PostgreSQL startup failed because its secret bind mount lacked usable permissions/SELinux labeling. Corrected the read-only labeled mount and reran health/persistence checks successfully. No privilege escalation or host package installation was necessary.
- Direct HP PDF download could not validate its TLS chain in this shell; did not disable verification. RAM recommendations cite an HP-authored QuickSpecs mirror and HP support documents. Privileged SMBIOS remained unavailable; installed slot/channel details are not invented.

## Packages and services

Project-local additions: pip-audit, Ruff, podman-compose and their locked dependencies; local setuptools upgrade. Full package versions are in `requirements.lock`. PostgreSQL 18 and Redis 7.4 images/volumes were created rootlessly. No system package, kernel, GPU driver or paid resource was changed.

Running services: dashboard 127.0.0.1:3000; FastAPI 127.0.0.1:8000; PostgreSQL 127.0.0.1:5432; Redis 127.0.0.1:6379. App project/memory/audit persistence still uses SQLite; merely starting containers does not imply PostgreSQL/Redis application adapters were built.

## Hardware, blockers and next milestone

HP EliteBook 830 G8, i5-1135G7, ~7.5 GiB visible RAM, ~1.5 GiB initially available and ~150 GiB initially free disk. No SSD purchase is required. Platform documents support replaceable DDR4-3200 SO-DIMMs up to 64 GB; 2×16 GB is a practical future memory target, with existing slot population/channel mode needing BIOS/technician verification. No purchase is needed for current runs.

No credential or privileged-operation blocker remains for this delivered CPU cycle. CUDA, AMP/DDP execution, instruction tuning, capable assistants/agents and multi-user production auth remain unimplemented. GPU expansion requires future hardware, approval and actual backend tests; see [GPU readiness](future-gpu-readiness.md).

Next: matched-token/multiple-seed experiments, broader reviewed source text with untouched final holdouts, then human-reviewed instruction data and executable task evaluation. See [roadmap](roadmap.md).

## Files changed

Core: `nexora/model.py`, `train.py`, `api.py`, new `artifacts.py`, `data_engine.py`, `research.py`, `research_api.py`, `jobs.py`, `scaling.py`. Existing config/dataset code formatted with behavior preserved outside documented repairs.

Tests: expanded API tests, new architecture/research tests, retained original smoke tests. Scripts: audit capture, bounded matrix, independent evaluation, isolated legacy benchmark, real worker lifecycle QA, rootless infrastructure helper, browser QA regression.

Config: reviewed source catalog, dependency manifests/lock, Compose, env template and ignore rules. Docs: audit, hardware/storage/RAM, dataset strategy, measured evaluation, research contracts, GPU plan, delivery evidence, updated README and roadmap. Frontend application source was not redesigned or changed in this cycle.
