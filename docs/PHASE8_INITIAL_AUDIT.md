# Phase 8 initial audit — 2026-10-19

Baseline `f9fe068`, clean research/phase2-model-reliability; remote matched before
branching to research/phase8-computer-use. All 90 baseline tests passed (13.84s).
Exact hardware and service observations: evidence/phase8/initial-audit.json.

Actual physical RAM is approximately 7.48 GiB, not 32 GB. The 32 GB figure was
an earlier assumption/purchase target, not evidence of installed memory. CPU is
an Intel i5-1135G7, 4 physical/8 logical cores, Intel integrated graphics, no CUDA.
Swap is heavily occupied. Do not infer usable compute from swap or GPU catalogs.
No large download or long training run is authorized by this phase.

Existing working slices: FastAPI/Next localhost UI; Ollama SmolLM2 reference;
FCC aliases routed to that reference; optional LocalAI (stopped); NIM Chat and
experimental Responses plus installed Riva client (no hosted key); SQLite chat
and owner memory; public search, extractive citations, read-only Playwright;
registered one-file Python code proposals, Podman verification and hashed owner
apply approval; daily revision discovery; immutable Core/model artifacts.

Phase 7 is not universally complete: documented SmolLM2 utility score 0/20,
Core tool choice 0/16, no JS/TS/PHP/container application execution profile,
no general browser interaction, no robust semantic citation verification.
Installed external runtimes do not provide proprietary Claude weights. REA is a
local project wrapper, not an instruction to inspect unrelated apps; current
Codex session has no REA tool namespace. Skills remain scoped reference workflows.

Checkpoint identity is verified in the JSON evidence. Selected Core remains
984,192 parameters, original architecture/tokenizer/data, not the tool-SFT
pilot. Earlier reports and failures remain intact. A new browser test profile,
retrieval index, and isolated bounded experiments will be recorded separately.
