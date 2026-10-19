# Phase10 delivery — 2026-10-19

Branch `research/phase10-reliability`, based on independently checked `f9c38b9`.
This delivers measured reliability improvements; professional coding and a stronger
sustainable assistant remain unmet. Read PHASE10_LIMITATIONS.md before enabling models.

Implemented exact minimal replacements with unique anchors/scoped paths; JSON validation;
scoped Python module imports; actual applied-tree sandbox retests and journaled rollback;
cross-process admission for managed training/inference; canonical search dedup/ranking;
redirect metadata and explicit unknown/unverified dates; literal citation/hash validation;
new benchmark/control runner; rights-reviewed disjoint-value Core experiments; focused
UI controls and Phase10 dashboard counts. No unrestricted host execution or paid fallback.

Results:116 tests passed32.14s; frontend type/build,Ruff F,pip check,health checks passed.
Real API streaming persisted; supplied two-file minimal control passed sandbox/approval/
post-apply checks. API restart preserved completed task, post-apply result and streamed final reply. UI browser checks passed. No professional model success inferred.

31-task final suite:0 passed,23 failed,8 blocked;23 supplied controls passed. A Python
isolated-import harness defect was corrected and stored proposals rescored without new
inference. TS typechecking controls exceeded existing sandbox budget and remain blocked.
Raw and corrected evidence retained. No claim this benchmark establishes generalization.

SmolLM2 external134.52M Q4_K_M remains selected reference.26 measured calls, median
84.64tokens/s, first delta0.771s,host sampled Ollama RSS sum peak377,528,320bytes;
service lifetime cgroup peak492,204,032bytes includes cache/earlier requests. Normal cap
943,718,400bytes=900MiB,swap0,two threads. Qwen stored/disabled; no new downloads.
NVIDIA catalog reachable, generation credential-blocked; no external API spend.

Original independent984192parameter checkpoint:
`artifacts/runs/phase2-small-language/checkpoints/step-0000400/model.safetensors`.
SHA256 `0b10d349fe2a8517544cd31cee03140eba7aa730fd1087ae01f0b02b1b56ee84`.
Reproduced validation4.403331668723472,test loss4.178615570217266,
perplexity65.27542139274378 across all held-out targets; exp(loss) verified.
New random-init pilots:
`artifacts/instruction-pilots/phase10-narrow-80/`,
`artifacts/instruction-pilots/phase10-diverse-80/`.
80steps each,train4.880/3.565seconds,CPU7.853/6.564seconds,peak313/312MiB,
sampled max68/69°C. Each8/8 tool identities but0/8 exact argument sets and4/24
instructions. Tokenizer/parameter totals differ; loss comparisons are confounded.
No promotion; original checkpoint untouched. No external weights relabeled Core.

Real keyless GitHub search and three public browser reads completed;three citations
passed exact-text/hash checks.20/20 deterministic supported/unanswerable fixtures passed.
These do not measure semantic truth or model hallucination. Retrieved pages never authorize
actions and are not automatically training data. Full public-source content stays in
private research artifacts; public evidence publishes URLs/hashes/status only.

## Exact commands

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check nexora tests scripts/phase10*.py scripts/build-phase10-benchmark.py --select F
.venv/bin/python -m pip check
export PATH="$PWD/.tools/node/bin:$PATH"
(cd frontend && npm run typecheck && npm run build)
scripts/start-local.sh api
# Separate terminal:
scripts/start-local.sh ui
.venv/bin/python scripts/health-local.py
.venv/bin/python scripts/phase10-ui.py
```

Destructive reruns are refused. Use a separate checkout/storage and preserve existing
records; scripts produce actual experiments, never synthetic performance metrics:

```sh
.venv/bin/python scripts/build-phase10-benchmark.py
.venv/bin/python scripts/phase10-evaluate.py
.venv/bin/python scripts/phase10-controls.py
.venv/bin/python scripts/phase10-memory.py
.venv/bin/python scripts/phase10-research.py
.venv/bin/python scripts/phase10-selected-core.py
.venv/bin/python scripts/phase10-core.py
.venv/bin/python scripts/phase10-live.py
.venv/bin/python scripts/phase10-document.py
```

The benchmark author refuses overwriting frozen fixtures. Memory sampler is intended to
run during the bounded final inference, not while training. Run other compute sequentially.
Managed overlap returns429,low available RAM503; external clients remain outside the gate.
Training implementation changes preserve inference but invalidate exact-code resume for
older runs; retain old commit for exact resumption or fork a new run.

Services:UI http://localhost:3001,API http://localhost:8000,Ollama11434,FCC8082.
LocalAI stopped,unrelated port3000 untouched. Weights/checkpoints/databases/secrets/private
conversations remain excluded from Git. Changed-file inventory:PHASE10_FILES.txt.

Next milestone: establish an explicitly authorized practical inference budget or configured
hosted provider; validate runtime controls before freezing a new final task-family holdout.
Improve diverse instruction arguments and prove exact task success before Core promotion
or larger pretraining. This phase does not resolve the weak model by adding platform features.

Exact experiment-time training source is archived in evidence/phase10/training-source.py; its SHA matches both recorded experiment code hashes. Final corrected grader/runtime identities are in final-code-hashes.json.
