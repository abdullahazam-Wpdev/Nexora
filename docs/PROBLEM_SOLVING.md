# Problem-solving agent and coding agent improvements — Phase 6 (not built this pass)

Phase 6 §7-8 ask for a reusable problem-solving workflow (decompose,
choose tools, run calculations, reproduce bugs, patch, test, compare
alternatives, retry with limits) and coding-agent improvements (repo
inspection, dependency analysis, patch review, lint/type-check/build
verification, fix iteration) on top of the existing sandboxed cowork
actions.

## Status: not implemented this pass

Not done, for the same reason as `docs/RAG_ARCHITECTURE.md`: this pass's
time went to finishing the search/browser/research vertical slice
completely and honestly (Milestones A-C) rather than starting this one
too, per Phase 6's own "finish each working vertical slice before
expanding" instruction. A real problem-solving/coding-agent loop with
retry limits and multi-step planning is itself a multi-session project,
and this project's own `docs/AGENT_CAPABILITIES.md` (Phase 4) already
documents why: "Reliable autonomous planning, repository-wide editing and
unattended agent creation remain research work."

## What already exists and is the right foundation to build on

- `nexora.cowork` already implements explicit, user-directed file read/
  write and the isolated `/run` sandbox with real resource limits
  (network disabled, read-only root, dropped capabilities, memory/CPU/
  time caps) -- the execution primitive a problem-solving loop would
  call, already live-verified working this project (coding category in
  `docs/AGENT_EVALUATION.md`).
- The new `nexora.research_agent` module is a working example of the
  exact shape Phase 6 wants for other workflows: a plain function doing
  real work, wrapped by a thin FastAPI router, with an audit log entry
  and a persisted evidence file per call. A problem-solving workflow
  should follow the same shape rather than a new pattern.

## Concrete next step, scoped for a future pass

1. A `nexora/problem_solving.py` module: given a task description, call
   existing primitives in sequence (read files, propose a patch as plain
   text, apply it only after an explicit approval step, run
   `nexora.cowork_sandbox.run_python` or project tests, report pass/fail).
2. Test it on a disposable sample project first, exactly as Phase 6 §8
   itself requires, before ever pointing it at NEXORA's own repository.
3. Add retry limits and a recorded tool-call trace (what was tried, what
   failed, what was retried) only once step 1-2 produce a working single
   pass -- retry logic on top of a broken single attempt just repeats the
   same mistake faster.
