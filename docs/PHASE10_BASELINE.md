# Phase 10 baseline — 2026-10-19

Starting commit f9c38b9, clean research/phase9-reliability; remote history matched
f9c38b94fc29523269a07b15cd8234f99ed85b66. Work branch research/phase10-reliability.

Commands: `.venv/bin/python -m pytest -q` → 107 passed, 18.94 seconds;
`.venv/bin/ruff check nexora tests --select F` → passed;
`cd frontend; npm run typecheck` → passed; `npm run build` → passed.
`npm run lint` is unavailable (no such script), not a passing lint check.
`python scripts/health-local.py` → API/UI/Ollama/FCC HTTP 200.

Measured physical memory 8,030,429,184 bytes = 7.4789 GiB, not 32 GB.
Available 1,162,104,832 bytes; swap 8,029,724,672 of 8,029,990,912 bytes used.
Four physical/eight logical cores. See evidence/phase10/system.json.
No new model download or memory-cap increase is authorized by this phase.
Ollama MemoryMax 943,718,400 bytes, swap zero, CPU quota two cores.
LocalAI stays stopped. NVIDIA credentials are not required for local operation.

Independent review of actual Phase9 benchmark records confirms corrected 2/17
model passes plus three blocked runtimes. The temporary 1152 MiB run completed;
three earlier 900 MiB runs OOMed. Phase10's premise that 1152 MiB failed is
incorrect. Qwen remains disabled, SmolLM2 is the external reference baseline.
Selected Core SHA remains
0b10d349fe2a8517544cd31cee03140eba7aa730fd1087ae01f0b02b1b56ee84.
Persisted completed multi-file task and streamed final text were read through API.
No Core promotion. Prior pilots and public evidence remain preserved.

Initial browser regression timed out on a disabled Send button while rebuilding
an already-running Next production server. UI was restarted against the completed
build; final browser result is recorded separately, not assumed from unit tests.

After restart, the original Phase9 browser chat/workspace/evaluation/Library regression passed. Final Phase10 browser fixture also passed minimal-edit selection and actual evaluation counts.
