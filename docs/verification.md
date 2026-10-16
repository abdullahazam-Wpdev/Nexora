# Verification — 2026-10-16

## Executed checks

- Hardware/environment: `uname -a`, `lscpu`, `free -h`, `df -h .`, `lsblk`, `lspci`, runtime and host os-release reads. See hardware report.
- Dependency setup: `python3 -m venv .venv`; pip installs of FastAPI/Uvicorn, tokenizers, safetensors, psutil, pytest, httpx, NumPy, Playwright and CPU PyTorch; local Node 22 archive verified with official SHA-256 manifest; `npm --prefix frontend install`.
- `python -m nexora.train --steps 160`: completed from random weights on local arithmetic fixture.
- `python -m nexora.train --resume --steps 10`: completed at total step 170 with saved optimizer and model state.
- `.venv/bin/python -m pytest -q`: **8 passed**. Covers causal masking, logits shape, finite gradients, single-batch overfitting, approval/secret rejection, dedup/split separation, safetensors equality, token generation, tokenizer Unicode roundtrip, actual training and resume, API persistence/audit, origin guard, validation and duplicate-ingestion errors.
- `npm --prefix frontend run typecheck`: passed.
- `npm --prefix frontend run build`: production build passed. Uses one build worker to reduce RAM pressure.
- `npm --prefix frontend audit --omit=dev`: zero reported vulnerabilities.
- `.venv/bin/python -m pip check`: no broken requirements.
- Browser QA: `python scripts/browser_qa.py`; see evidence/browser-results.json and PNG screenshots for final results.

## Measured model result

143,808 parameters; 2 blocks; width 64; 4 heads; context 64; 289 learned vocabulary entries (384 upper target); CPU float32; two threads; microbatch 4 and accumulation 2. Fixture contains 128 unique documents and no external corpus. Document-level split occurs before tokenizer training; only training documents train BPE.

Training loss: 5.768411 at step 1 → 0.469730 at step 160 → 0.467866 at resumed step 170. Final sampled validation loss 1.076080; sampled held-out test loss 1.151963. Validation and test are one random packed batch per measurement, not full-corpus benchmark averages. They must not be presented as general language quality. The recorded `seconds` field measures the latest invocation, not cumulative training time. Evidence JSON preserves the actual run history.

## Issues found and fixed

The first checkpoint save failed because safetensors needed NumPy at runtime. Added NumPy to the project manifest, installed it, reran training and all tests successfully. Initial Next.js dependency audit found one moderate and one high advisory; updated Next.js and reran audit, obtaining zero reported findings. First browser check could not locate a navigation button because its badge altered its accessible name; explicit navigation labels fixed it. Screenshot review found an overly broad SVG width selector stretching panel icons; scoped it to chart SVGs and rebuilt. One build invocation was rejected by the Next.js build lock while a preceding build finalized; reran sequentially successfully.

## Services

- FastAPI/Uvicorn: 127.0.0.1:8000.
- Next.js production dashboard: 127.0.0.1:3000, same-origin API proxy.
- No PostgreSQL or Redis process started. Rootless Podman unavailable in the execution environment; supplied Compose configuration remains untested.

## Limitations and next work

The verified environment is the VS Code Flatpak execution environment on Fedora, not an unrestricted host terminal. No system packages, drivers, kernel changes or privileged actions performed. Approximately 2 GiB of workspace dependencies were installed, plus browser binaries in the application cache. RAM is the principal scaling constraint. No credentials, paid APIs, public exposure or external dataset download required.

Single named checkpoint is replaced by a fresh run; concurrent direct CLI/API training is not coordinated. Do not run multiple trainers against one artifact root. Training status only tracks processes launched by the current API lifetime; failed jobs leave diagnostics in artifacts/training.log. Full production job recovery, complete data policy validation, production auth and PostgreSQL adapters remain pending.

Next milestone: multi-run registry and durable job state, selectable approved training datasets, full-corpus evaluation and stronger project permissions. See roadmap for all later phases.
