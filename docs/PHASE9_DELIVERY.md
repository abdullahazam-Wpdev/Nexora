# Phase 9 delivery — 2026-10-19

Baseline verified at `35b212b`; work is on `research/phase9-reliability`.
This phase delivers real reliability work and negative/positive measurements,
**not a professional assistant or a promoted Core 2.0 model**. Several requested
capability targets remain unmet; see PHASE9_LIMITATIONS.md.

## Results

| Area | Measured result |
| --- | --- |
| Phase 8 regression reproduction | 96 tests; real browser/PNG hash; sandboxed addition, wrong-hash rejection and approval; retrieval 3/3; standard 0/3 vs concise 1/3 coding |
| Phase 8 wider Core tool reproduction | 6/16 correct, 14/16 valid schema |
| New Qwen original arithmetic regressions | 3/3, exposed development tasks |
| Corrected expanded mixed-language suite | 2/17 model passes under owner-approved temporary 1,152 MiB profile; supplied controls 17/17; 3 blocked runtime cases |
| Default-cap one-file protocol regression | 1/17; not a clean untouched final evaluation |
| Candidate inference performance | Median first-token 2.113 s, decode 36.46 tokens/s; cgroup peak approximately 1,152 MiB, including cache |
| Sustained normal-cap operation | Qwen hit 900 MiB OOM three times; disabled by default; normal 900 MiB service restored |
| Core tool-only 80-step experiment | 5/16, below the old 6/16 target; not promoted |
| New explicit-argument instruction pilot | 5/11 correct tool identities with strict schema, 1/11 exact tool+arguments, 0/8 exact instructions |
| Pilot repeat | Every checkpoint tensor and dataset SHA identical |
| Expanded source-field retrieval | 20/20, literal extraction/conflict/date/deletion/injection fixtures, not semantic QA |
| Tool proposal probes | SmolLM2 0/22; Qwen only 4 recorded cases before resource failure, not a complete score |

The original apparent 3/17 mixed-suite score included a vacuous HTML test. A real
rescore of the stored candidate removed that false success, producing **2/17**.
Raw initial grade and corrected results are retained. No blocked inference or
missing runtime is marked as passing. Diagnostic resource-failed runs are not
complete capability comparisons. Different Core tool protocols are not compared
as a single percentage.

## Implemented behavior

- Pinned, attributed Qwen candidate adapter; streamed Ollama deltas and persisted
  final conversations, partial-stream failure rejection, bounded buffers and
  cooperative stop. Default SmolLM2 chat now uses real streaming. Qwen is visibly
  disabled after normal-cap failures, with no silent paid/model fallback.
- Scoped multi-file coding engine/API/UI with up to four existing registered
  files, minimal candidates, preserved prompts/responses/proposals, strict path
  scope, actual Python/Node/TypeScript acceptance, diff/test review, exact bundle
  approval, intent journal, rollback and concurrent-owner-edit protection.
- Rootless networkless language profiles reuse the pinned Python image and the
  existing Node/TS installation; no system-wide dependency or extra image pull.
  Shared temporary staging fixes the Flatpak/host /tmp visibility problem.
- Twenty original coding tasks plus held-out-from-proposer acceptance/control
  fixtures. Coverage/blocked profiles, invalid format/logic failures and harness
  correction are documented in CODING_BENCHMARK.md.
- Eleven strict tool argument schemas and a permission-separated validation API.
  Calculator/retrieval/scoped reads execute; privileged or unsupported operations
  remain proposals through the proper approval workflows. No shell executor.
- Publication-date column migration for existing document DBs, explicit key:value
  evidence, conflict/missing/outdated/unknown-date handling and real source IDs.
  Date metadata is owner supplied, not externally authenticated.
- Three separate short Core designs and an exact repeat, original CC0 synthetic
  provenance/splits/hashes, completion-only losses, strict tool/argument tests and
  untouched production Core. No architecture/size promotion from low loss.
- Updated provider registry, workspace coding panel, disabled-candidate controls,
  reliability dashboard and the existing coding skill. Existing chat/approval,
  browser, library, model/speech views and training dashboard remain available.

## Verification

**107 automated tests passed** (final rerun: 17.52 seconds), including original 96 regressions
and new schema, streaming persistence, incomplete-stream recovery, multi-file
apply/rollback/concurrent-edit, Node/TS, missing-task and database migration/date
cases. Ruff F checks and `pip check` passed. Frontend typecheck and production
build passed. Live API integration verified 24 real SmolLM2 delta frames, persisted
final text, and a **supplied-control** two-file Podman test/diff/apply, including
wrong approval rejection. Controls are not model intelligence successes. Browser UI checks passed for real streamed chat, disabled candidate selection, workspace coding, corrected evaluation metrics and Library. After restarting the API, the completed multi-file task and streamed final reply persisted.

Services: API localhost:8000, UI localhost:3001, Ollama localhost:11434 and FCC
localhost:8082. LocalAI remains stopped; NVIDIA hosted model/speech calls remain
credential-blocked. Ollama MemoryMax is restored to 943,718,400 bytes (900 MiB),
MemorySwapMax zero, CPU quota 200%, one loaded model. The approved temporary
1,152 MiB study completed; its profile file was removed. No larger standing budget
is assumed. No new paid inference, private-chat training or GPU provisioning.

## Exact commands

Run API/UI in separate terminals after a production build:

```sh
scripts/ollama.sh start
scripts/fcc.sh start
scripts/start-local.sh api
scripts/start-local.sh ui
.venv/bin/python scripts/health-local.py
.venv/bin/python -m pytest -q
.venv/bin/ruff check nexora tests scripts/phase9*.py scripts/build-phase9-benchmark.py scripts/prepare-node-sandbox.py --select F
.venv/bin/python -m pip check
export PATH="$PWD/.tools/node/bin:$PATH"
(cd frontend && npm run typecheck && npm run build)
```

Reproduction scripts preserve existing output/fixture directories where applicable;
use fresh labels/run IDs for repeat studies and leave earlier evidence intact:

```sh
.venv/bin/python scripts/prepare-node-sandbox.py
.venv/bin/python scripts/phase9-baseline.py
.venv/bin/python scripts/phase9-baseline-integration.py
.venv/bin/python scripts/phase9-code-eval.py qwen-coder FRESH_LABEL
.venv/bin/python scripts/phase9-rescore-html.py
.venv/bin/python scripts/phase9-retrieval-eval.py
.venv/bin/python scripts/phase9-tool-eval.py FRESH_LABEL
.venv/bin/python -m nexora.instruction_pilot
.venv/bin/python scripts/phase9-repeat-pilot.py
.venv/bin/python scripts/phase9-live-integration.py
.venv/bin/python scripts/phase9-ui-check.py
```

Qwen evaluation is intentionally disabled in the final manifest; do not change its
flag or raise service limits to reproduce automatically. A fresh explicit resource
review/authorization is required. `OLLAMA_SERVICE_MEMORY_MIB=1152` is the reviewed
optional launch profile used only for the authorized study; default remains 900.
The already downloaded model is retained for future authorized research.

## Checkpoints, data and file inventory

Selected immutable Core:
`artifacts/runs/phase2-small-language/checkpoints/step-0000400/model.safetensors`.
Original SHA remains `0b10d349fe2a8517544cd31cee03140eba7aa730fd1087ae01f0b02b1b56ee84`.
New, unpromoted pilots:
`artifacts/tool-sft/phase9-tool-80/`,
`artifacts/instruction-pilots/phase9-mixed-instruction-80/`,
`phase9-mixed-explicit-80/`, and `phase9-mixed-explicit-repeat-80/`.
Each retains actual dataset/tokenizer/checkpoint/result records. New tool-only
training: 3,200 supervised targets; explicit mixed pilot: 3,649 targets, 80 steps,
387,552 parameters, approximately 351 MiB monitored RSS and sampled 68°C maximum.

Public fixture evidence is `docs/evidence/phase9/`; private task state/originals
are `artifacts/agent-tasks/`, `workspace-code/` and disposable repos in
`artifacts/phase9/`. Source-field DB remains private `artifacts/documents.sqlite3`.
Weights, runtime library copies, private databases and credentials are excluded
from Git. Exact changed-file inventory is `docs/PHASE9_FILES.txt`.

## Phase 10 recommendation

First establish a sustainable practical assistant resource budget or explicitly
configured capable hosted backend. Freeze a fresh, stronger task-family holdout
before selection. Then expand one verified framework profile and improve diverse
rights-reviewed instruction/argument data. Core's validation/test gap and failed
argument/instruction cases must improve before promotion or larger pretraining.
