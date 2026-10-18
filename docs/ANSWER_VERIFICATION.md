# Verification engine — Phase 6 (partially exists, not built as a unified engine this pass)

Phase 6 §13 asks for task-specific verification across code, calculations,
research, structured data and agent tasks, visible in the chat UI.

## What already exists today, scattered across the project

| Area | Existing verification | Where |
| --- | --- | --- |
| Code | Real sandboxed execution with exit-code checking | `nexora.cowork_sandbox.run_python`, exercised live in `docs/AGENT_EVALUATION.md`'s coding category |
| Checkpoints | sha256 integrity, strict tensor-shape loading, finite-value check, tied-weight equality | `nexora.research.verify_checkpoint`, independently re-run in `docs/phase5-system-audit.md` |
| Datasets | Hash-pinned files, approved-license check, dedup | `nexora.data_engine.load_dataset` |
| Research/citations | Read-status per citation (`read`/`failed: <reason>`), never a fabricated excerpt | `nexora.research_agent`, this pass |
| Structured JSON | Exact-match scoring against a schema in the eval harness | `scripts/agent_eval.py`'s `structured_json` category |
| Input validation | Pydantic `Field` bounds on every API endpoint added this project | throughout `nexora/*.py` |

## What is not implemented: one unified verification engine

A single `nexora/verification.py` that any task type routes through
(lint, type-check, build, independent recomputation for math, schema
validation for structured data, acceptance-criteria evaluation for agent
tasks) does not exist yet. Today each subsystem does its own checking in
its own way, which works but is not a reusable, UI-visible verification
layer. Building that unification is real design work (a common
verification-result shape, a registry of checkers per task type) that
was not done this pass -- the search/browser/research vertical slice
took priority, per Phase 6's own execution-order instruction.

## Linting/type-checking/build verification specifically

`ruff check`/`ruff format` are used throughout this session's own work
(see every Phase 6 commit) but are not yet exposed as a callable
verification step the coding agent invokes on a user's code -- that is
part of the coding-agent improvements in Phase 6 §8, not done this pass
(see `docs/PROBLEM_SOLVING.md`).

## Honest conclusion

Verification exists in depth where it matters most right now (checkpoints,
datasets, sandboxed code execution, citations) and is absent as a single
UI-visible subsystem. The next real step is wiring the existing per-area
checks into one shared result shape (`{passed, checks: [...], evidence}`)
that the frontend can render consistently, not inventing new checking
logic from scratch.
