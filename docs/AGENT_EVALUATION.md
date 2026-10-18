# Agent evaluation suite — Phase 5

## Phase 6 update

The local-model generation length caps this suite's backends hit have
since been raised (`docs/PHASE6_DELIVERY.md`) -- the scores below were
measured before that change and have not been re-run after it, since the
caps were not the cause of the near-zero scores (coherence and
correctness, not truncation, is why both backends fail most categories).
Phase 6 also adds three new real capabilities -- live web search
(`docs/WEB_SEARCH_INTEGRATION.md`), browser reading
(`docs/BROWSER_AUTOMATION.md`), and the research agent
(`docs/RESEARCH_AGENT.md`) -- none of which are part of this automated
suite yet. "Source attribution" and "current-information research," both
named in Phase 6 §16's requested benchmark categories, are not yet
represented here; the research agent's own test suite
(`tests/test_research_agent.py`) covers correctness of the pipeline
mechanics (no fabricated citations, failures are recorded) but not answer
quality against a held-out question set. That is the right next addition
to this file, not done this pass.

Real, automated, bounded test cases run live against two actual backends
this session: **NEXORA Core** (`phase2-small-language` checkpoint, 984,192
parameters) and **Ollama / SmolLM2 135M** (the pinned external reference).
Harness: `scripts/agent_eval.py`. Raw evidence:
`artifacts/evaluation_suites/phase5-agent-eval/results.json`. Every score
below is from that run, not estimated.

```
PYTHONPATH=. .venv/bin/python scripts/agent_eval.py
```

## Scores (2026-10-18, this session)

| Category | NEXORA Core | Ollama SmolLM2 135M | Scoring method |
| --- | --- | --- | --- |
| Instruction following | 0/5 | 2/5 | Exact substring match against a required literal answer |
| Structured JSON generation | 0/2 | 0/2 | Must emit valid, exactly-matching JSON |
| Tool selection | 0/3 | 1/3 | Must name the correct `/write`, `/read` or `/run` command for a described task |
| Multi-turn memory (in-context recall) | 0/2 | 1/2 | A fact stated earlier in the same prompt must be correctly recalled |
| Refusal to invent | 3/3* | 1/3 | Heuristic: hedge/decline language, or no fabricated specific number |
| Python coding + real sandbox execution | 0/2 | 1/2 | Generated code is **actually run** in the rootless Podman sandbox; pass requires exit code 0 and correct stdout |

\* **Caveat, read before citing this number**: NEXORA Core's 3/3 on
"refusal to invent" is a scoring artifact, not genuine epistemic behavior.
Its real output for that prompt is
`"the particular function is not be used to the file object. This is a\nindex object, the module is a new object is"`
-- incoherent text that happens to contain no fabricated digit sequence, so
the keyword heuristic scores it as "didn't fabricate a number." It is not
declining or hedging; it is incapable of answering at all. Treat Core's row
on this category as **not meaningful**, not as a capability.

## What this demonstrates, plainly

- **NEXORA Core cannot currently perform any of these six categories.**
  Every genuine pass (0/5, 0/2, 0/3, 0/2, 0/2) is zero except the one
  artifact above. This matches `docs/model-evaluation-report.md`'s own
  generation samples (`"Python is contual environment, and are not
  handless..."`) -- a next-token research model with no instruction-tuning,
  not a partial failure being undersold.
- **SmolLM2 135M, a real instruction-tuned open-weight model, does
  genuinely better but still fails most categories.** Its one clear win:
  asked to write `add_numbers(a, b)` and print the result, it wrote correct,
  different-but-valid code (`def add_numbers(*args): return sum(args)`)
  that **actually executed successfully in the real sandbox** and printed
  the right answer. Asked for a harder string-reversal task, it wrote code
  with a syntax error that the sandbox genuinely caught (`SyntaxError`,
  exit code 1) -- a real, not simulated, failure.
- This also **live-verifies the rootless Podman sandbox for the first time
  this project has specifically exercised it in this session**: the
  `nexora.cowork_sandbox.run_python` path was called fresh, outside any
  prior cached test, and correctly executed, isolated, and reported both a
  passing and a failing program.

## Categories from the Phase 5 request not implemented this pass

`general_chat_quality`, `document_question_answering`,
`javascript_typescript_coding`, `wordpress_development`,
`woocommerce_workflows`, `shopify_development`, `multi_step_task_planning`,
`error_correction`, `research_with_citations`, `safe_agent_behavior`.

Reason, stated plainly: building representative test cases and a defensible
automated scorer for each of these (especially the WordPress/WooCommerce/
Shopify and citation-research categories) is its own multi-session project,
and running them now against two backends that already fail basic
instruction-following would mostly produce zeros that teach nothing new.
The six categories above were chosen because they're automatable with exact
or sandbox-verified scoring (no LLM-judge needed) and because together they
already establish the headline finding: **neither available backend is a
usable general assistant yet**, which is the one thing Phase 5 requires not
be glossed over.

## Baselines and regression use

This run is the baseline. Re-run `scripts/agent_eval.py` after any Phase 5
training or instruction-tuning change and diff
`artifacts/evaluation_suites/phase5-agent-eval/results.json` against this
doc's numbers -- a regression is any category score that drops for either
backend. The harness is deterministic for Ollama (`temperature=0, seed=42`)
and for Core (greedy `model.generate`), so re-runs should reproduce exactly
absent a real model/prompt change.

## Limitations of this harness, stated directly

- Scoring is keyword/exact-match/sandbox-exit-code based, not a semantic
  judge. "Refusal to invent" in particular is a weak heuristic (see caveat
  above) -- a model that rambles incoherently can score as "not fabricating"
  without actually exhibiting calibrated uncertainty.
- Small sample sizes (2-5 cases per category) establish a directional
  baseline, not a statistically powered benchmark.
- "Multi-turn memory" here means in-context recall within one prompt, not
  persistent cross-request session memory -- an honest naming of what a
  single-shot `generate()` call can actually test.
