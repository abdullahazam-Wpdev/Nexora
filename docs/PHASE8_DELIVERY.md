# Phase 8 delivery — 2026-10-19

Continued from verified `f9fe068` on feature branch
`research/phase8-computer-use`. The Phase 8 request is **partially implemented**:
the real browser/coding/retrieval/research vertical is delivered; reliable general
intelligence and every listed language/application profile are not demonstrated.
See PHASE8_INITIAL_AUDIT.md for the independent baseline audit and exact hardware.

## Delivered behavior

- Durable approval-bound isolated browser tasks with fixed dependencies,
  observations, screenshots, cancellation, recovery and action/time/retry limits.
  Browser workspace supports actual task plans and approval/history/evidence.
- Real disposable-form navigation/typing/clicking/assertion/screenshot demo:
  1.10 seconds, sampled process-tree peak approximately 611 MiB. Screenshot was
  visually inspected. Arbitrary account/desktop interaction is unsupported.
- Existing coding lifecycle now records structured plan/constraints and 24-action
  budget. Experimental concise prompt is selectable; sandbox/approval unchanged.
- Actual Python addition repair using public Python documentation, a real
  SmolLM2 proposal, visible diff, Podman acceptance, wrong-hash rejection and
  correct approved apply. It took 9.72 seconds. Original/candidate and journal are
  retained in its disposable task directory.
- Measured single versus role workflow: 0/3 versus 0/3; 3/3 supplied controls;
  concise ablation 1/3. More roles did not improve this baseline. An invalidated
  harness-development run is retained separately and excluded from scores.
- SQLite FTS5 owner document ingestion/search/deletion, project boundaries,
  content hashes and stable chunk citations in Library; three smoke queries pass.
- Four bounded, independent Core pilots: 78,480 / 171,328 / 171,328 / 336,864
  parameters, 40 steps each, 1,600 supervised completion tokens, validation,
  held-out masked perplexity, JSON/tool checks, CPU/RSS/thermal/throughput and
  checkpoint measurements. Wider: 6/16 tools, not promoted. Peak observed pilot
  RSS below 352 MiB, sampled CPU temperature at most 59°C.
- Original 984,192-parameter Core checkpoint unchanged. Batched test perplexity
  65.275421 (rounding-level difference from 65.275419). Four strict instructions
  remain 0/4; external SmolLM2 also scored 0/4 and failed one recall probe.
- Eighteen-source/816-token authored six-category corpus with license, source
  hashes, splits, dedup/quality/contamination checks; deliberately not mixed into
  the Core matrix or represented as a meaningful foundation corpus expansion.
- New validated project browser skill; existing local REA MCP verified with 207
  tools, version 6.7.0 and Hopper available. No global configuration change or
  blanket MCP installation. Health script and source-preserving reproduction commands.
- Evaluations panel shows measured Core comparisons; the existing training
  dashboard remains at `/research`. Existing chat, model catalog, speech, memory,
  research citations and code diff/apply views are preserved.

## Final verification

Full Python suite: **96 passed** (15.47 seconds); the final affected browser and
document subset was rerun after the last boundary changes. Ruff F checks,
`pip check`, TypeScript and production Next build passed. Live UI workflows
passed, and actual API restart preserved completed coding/browser tasks. API,
UI, Ollama and FCC health checks returned 200. LocalAI remains stopped; NVIDIA
hosted inference and Riva recognition remain credential-blocked, not passing
model evaluations. The source-held-out corpus check and new skill validation
passed. No leftover demonstration Podman containers were observed.

## Evidence, commands and paths

Run the existing API/UI in separate terminals:

```sh
scripts/ollama.sh start
scripts/fcc.sh start
scripts/start-local.sh api
scripts/start-local.sh ui
.venv/bin/python scripts/health-local.py
.venv/bin/python -m pytest -q
.venv/bin/ruff check nexora tests scripts/phase8*.py scripts/health-local.py --select F
.venv/bin/python -m pip check
export PATH="$PWD/.tools/node/bin:$PATH"
(cd frontend && npm run typecheck && npm run build)
```

Research/demo commands (existing evidence/fixtures are preserved, so choose a new
run name/location for repeated coding demos instead of replacing old records):

```sh
.venv/bin/python scripts/phase8-browser-demo.py
.venv/bin/python scripts/phase8-coding-comparison.py
.venv/bin/python scripts/phase8-prompt-probe.py
.venv/bin/python scripts/phase8-coding-demo.py
.venv/bin/python scripts/phase8-core-study.py
.venv/bin/python scripts/phase8-quality-eval.py
.venv/bin/python scripts/phase8-data.py
.venv/bin/python scripts/phase8-report.py
.tools/node/bin/node scripts/verify_rea_mcp.mjs
```

Exact changed-file inventory: `docs/PHASE8_FILES.txt`.

Public fixture evidence: `docs/evidence/phase8/`. Browser task ID
`84589e5064d44f43940deb38068169ff`; screenshots under its
`artifacts/computer-tasks/` directory. Coding task ID and exact approved diff
are in `evidence/phase8/coding-demo.json`; task state/original/candidate/journal
under `artifacts/agent-tasks/<id>/`. Demo repository:
`artifacts/phase8/verified-coding-demo/`. New Core checkpoints/tokenizers/data:
`artifacts/tool-sft/phase8-{compact,baseline,balanced,wider}-40/`. Selected Core:
`artifacts/runs/phase2-small-language/checkpoints/step-0000400/`.

## Limits and incomplete requested scope

No stronger local/hosted assistant was added: current memory is constrained and
NVIDIA credentials remain absent. There is no unrestricted autonomous planner,
general desktop agent, personal account browser, multi-file JS/TS/PHP application
build profile, broad WordPress/WooCommerce/Shopify workflow, model-generated
permission authority, automatic training on conversations, semantic source
agreement/publication-date verifier, vector retrieval or public multi-user auth.
Browser process memory has monitoring, not a hard OS cap; DNS rebinding and
localhost-only trust assumptions remain documented. Service launchers are
foreground processes, not verified boot-persistent system services. No account
login, cloud provisioning, spending, new large data/model download or long run.

Phase 9: evaluate a stronger explicitly identified and authorized assistant
backend on untouched utility tasks, then broaden one reviewed multi-file sandbox
profile. Expand diverse rights-reviewed data, preserve unseen task-family tests,
repeat seeds and test real arguments/recovery before considering a larger Core
training budget or GPU purchase. Do not infer foundation-model capability from
low masked JSON perplexity or the one successful addition demonstration.
