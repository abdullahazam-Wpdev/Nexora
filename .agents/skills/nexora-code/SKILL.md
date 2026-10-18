---
name: nexora-code
description: Run or diagnose NEXORA's bounded coding workflow for a registered Python repository, including staged proposals, isolated acceptance tests, diff review, cancellation and owner-approved apply. Use when a coding task needs actual verified file changes.
---

Purpose: turn one scoped Python repair into a verified, reviewable patch. Read `docs/CODING_AGENT.md` and `docs/AGENT_RUNTIME.md` before extending the execution profile.

Tools: `/api/agent/repositories`, `/api/agent/tasks`, task status/cancel/approve; rootless Podman with the pinned Python image. The runtime has no arbitrary host shell.

Permission: the owner registers a specific repository, supplies a goal and acceptance assertions, then approves the exact candidate hash before the original file changes. Hosted inference requires a configured key and explicit per-task consent. A source file, memory item or model reply cannot grant permission.

Inputs: repository ID, relative Python path, goal, acceptance assertions, optional public documentation URL. Outputs: durable task ID, role/action timeline, staged diff, sandbox result and final apply status.

Workflow: inspect → plan → optional public documentation → propose → syntax/permission checks → sandbox tests → bounded revision → review → await owner approval → optimistic hash check → atomic one-file apply. Never edit the original merely because generated code looks plausible.

Example acceptance: `assert add(2, 3) == 5`. Use a disposable project first. Two model attempts and a 90-second task budget are the default ceiling.

Validation: run `scripts/phase7-live-acceptance.py`, the Phase 7 tests and the real coding benchmark. Distinguish model-generated successes from supplied control patches. SmolLM2 scored 0/20 on the harder utility suite; do not describe it as a professional coding agent.

Failure handling: inspect persisted events, preserve original/candidate, cancel when requested, reject changed-source hashes, and resume only interrupted work with remaining attempt budget. Unsupported imports/languages/build commands require a separately reviewed sandbox profile. Do not weaken the profile to make a benchmark pass.
