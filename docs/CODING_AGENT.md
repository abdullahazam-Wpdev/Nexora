# NEXORA Code

The working slice edits one registered Python source file. Register a specific project directory, then submit a goal and executable acceptance assertions through the UI's NEXORA Code view or `/api/agent/tasks`. A proposed diff appears only after syntax/profile checks and sandbox tests pass. Review and approve its exact candidate hash; changed source or candidate hashes are rejected. Unapproved candidates never overwrite original files.

The pure-Python profile permits selected stdlib transforms and blocks dynamic execution, filesystem access, unsafe imports and dunder introspection. Acceptance code itself runs only inside the existing rootless, networkless, read-only Python sandbox with CPU/RAM/process/time/output limits. The profile intentionally cannot run arbitrary package installs, JS/TS application builds, WordPress/PHP, Shopify mutations or host troubleshooting commands. `/api/agent/workflows` reports these as proposal-only rather than claiming implementation.

Models are independent of the workflow: local Ollama, independent research Core, or explicitly approved/configured GPT-OSS-20B through NVIDIA. No paid fallback. Owner-supplied patches use the same testing/approval path and are labeled separately from model proposals.

The actual end-to-end demonstration used an approved disposable repository in `artifacts/phase7/acceptance-repository`: read Python documentation → propose an addition fix → fail/revise → pass acceptance assertions → review diff → reject a wrong approval hash → approve/apply. All role actions and test output are retained in `docs/evidence/phase7/live-acceptance.json`.

Benchmark commands:

```sh
.venv/bin/python scripts/phase7-coding-benchmark.py --suite coding-v1
.venv/bin/python scripts/phase7-coding-benchmark.py --suite coding-v2
.venv/bin/python scripts/phase7-live-acceptance.py
```

`coding-v1` is a transparent microtask smoke suite whose prompt includes the required expression; SmolLM2 passed 4/20. `coding-v2` contains 20 bounded HTTP/API, commerce, parsing and documentation utilities with deterministic assertions; solution/control patches and tests are not sent to the model. SmolLM2 passed **0/20**. Supplied controls passed 20/20 on both suites. This validates the execution machinery, not professional autonomous coding capability. Multi-file edits, symbol indexing, arbitrary linters/build systems and semantic code review remain unsupported.

Registered-source inspection APIs also list at most 200 supported files within a 2,000-file scan budget, excluding hidden paths, symlinks and dependency/build directories. Read a selected file (16 KB maximum) and extract Python function/class names without executing it. Static source reads support Python/JS/TS/TSX/PHP/Markdown; this does not grant those languages an execution/build profile. Candidate tests and baseline controls remain separate from private repositories.

## Phase 8 verification

Structured step dependencies, constraint metadata and a 24-action limit are now
recorded with new tasks; older tasks remain readable. `prompt_style: concise`
is an explicit experimental alternative in the Code panel. It passed 1/3 simple
arithmetic smoke cases versus the standard workflow's 0/3, and completed the
recorded addition demonstration with real public documentation, sandbox tests,
wrong-hash rejection and approved apply. This does not establish professional
coding capability. See MULTI_AGENT_EVALUATION.md and evidence/phase8/coding-demo.json.

Execution still supports one pure Python module. JS/TS, FastAPI/Next application
builds, WordPress/WooCommerce/Shopify, container configuration and multi-file
changes remain proposal-only; no unrestricted host fallback was introduced.

## Phase 9 scoped workspaces

`/api/workspace-code/tasks` supports up to four existing registered files and
pure Python, Node modules, TypeScript runtime, Web Response unit and HTML/CSS
static profiles. Node runs inside the existing rootless networkless Podman image
using read-only runtime/compiler mounts. PHP/WordPress/FastAPI profiles remain
blocked. Tests, candidate files, originals and per-attempt prompts/responses are
retained. Exact bundle hash approval and unchanged-source checks precede apply;
an intent journal supports rollback and preserves concurrent owner changes.

The Workspace Code panel exposes scope, acceptance tests, diff, output, approval
and cancellation. Qwen is disabled by default after resource failures; selecting
SmolLM2 does not imply capable coding. Validation/controls prove the engine, not
model competence. See CODING_BENCHMARK.md and PHASE9_LIMITATIONS.md.

Phase10 adds optional exact replacements (`patch_format: edits`) and repeats sandbox
acceptance on the actually applied files before marking completion. Failed verification
rolls the journal back. New JSON/YAML/Markdown path scope does not imply YAML runtime
support. Python imports are allowed only for explicitly scoped top-level modules or the
existing stdlib list. See CODING_AGENT_RELIABILITY.md; do not treat supplied controls as
model successes. Final frozen model benchmark:0/31 passed,8 blocked.
