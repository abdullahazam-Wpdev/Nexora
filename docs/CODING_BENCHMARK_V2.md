# Frozen coding benchmark v2

31 original fixture tasks, frozen before the Phase10 proposer work and final inference.
`benchmarks/phase10/tasks.json`, `acceptance.json`, `freeze.json` retain exact hashes,
requests, existing-file scope, budgets and pass rules. Acceptance and supplied control
patches are not included in model prompts. Development uses the already-consumed
Phase9 suite. A final run has one proposal per task and refuses overwriting evidence.
Freeze author-code hash refers to the pre-format authoring source; subsequent formatting
is not represented as an unchanged byte hash. Acceptance files remain hash-identical.

Python transforms, API helpers, permissions, multi-file imports, JS, strict TS diagnostics,
HTML/CSS, JSON, Markdown and commerce-unit fixtures are included. FastAPI, PHP,
WordPress PHP, React/Next rendering and YAML execution remain explicitly blocked.
Web Response and commerce utilities are unit profiles, not framework deployments.

Raw run: {'passed': 0, 'failed': 26, 'blocked': 5}. Python controls subsequently exposed missing /workspace
on sys.path under Python -I. Fixed inside the container, preserving isolation. Stored
proposals were rescored without any new inference. Three strict TS control programs
failed within the existing 10s/256MiB profile and become harness blocks, not model failures.
Corrected: **0 passed, 23 failed,
8 blocked / 31 total**. Supplied controls: 23 passed.
Do not remove blocked cases from the headline denominator or call this a pristine
validated professional benchmark. Final fixtures are now consumed; no further tuning
or backend selection used their outputs. Next model selection requires a fresh suite.

Raw task IDs, attempt events, timings, invalid-patch/timeout categories and inference
metrics remain in `evidence/phase10/coding-final.json`; corrected assertions/control
outputs remain in coding-rescore.json. Agent RSS field is a snapshot, not a measured
peak. Tool counts count sandbox invocations, not inferred reasoning steps. Final scorer
source and runtime revisions are committed; frozen acceptance code has SHA-256 hashes.

Reproduce in a fresh checkout/storage directory, never overwrite old evidence:
`.venv/bin/python scripts/phase10-evaluate.py`, then `scripts/phase10-controls.py`.
The harness correction changes supported module imports, not model prompts or targets.
