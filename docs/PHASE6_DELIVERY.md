# Phase 6 delivery — web research, verified answers

Run 2026-10-18 against `research/phase2-model-reliability`, starting
commit `68c9340`. Per Phase 6's own execution order ("finish each working
vertical slice before expanding, do not begin every subsystem
simultaneously"), this pass completed Milestones A, B and the start of C
in full, real depth, and explicitly did not start D-H. Every claim below
has evidence; nothing is a projected or assumed result.

## Milestones actually completed

**A — Audit**: `docs/phase6-initial-audit.md`. Re-confirmed the 7.5 GiB
RAM figure a fourth time across sessions, found and reported a failed
background download (DNS resolution error, not caused by this pass),
and checked real network reachability for the hosts that matter to this
pass's own work -- not a generic "network is fine" claim.

**B — Internet (one real search provider + browser reader)**: done with
four working providers, not one. `nexora/search.py` live-verified against
Wikipedia, arXiv, Crossref and GitHub search, all credential-free, with
retries, caching, dedup, per-provider health checks, and an evidence file
per call. Caught and fixed a real bug along the way (Wikipedia's API
etiquette requires a descriptive User-Agent; the default one was silently
403'd). `nexora/browser_reader.py` live-verified navigating to a real
Wikipedia page, extracting real text, headings and links, with an SSRF
guard verified against `127.0.0.1`, `localhost`, and the cloud metadata
address `169.254.169.254`. Full detail:
`docs/WEB_SEARCH_INTEGRATION.md`, `docs/BROWSER_AUTOMATION.md`.

**C — Research (started)**: `nexora/research_agent.py` implements the
real question → search → read → cite pipeline and was live-tested end to
end with a real question, producing 3 real citations with real retrieved
excerpts. Caught and fixed a second real bug mid-build: the initial page
excerpt was grabbing Wikipedia's navigation chrome instead of article
text, verified wrong, fixed, verified right. The "answer" is explicitly
an extractive summary, not model-composed prose -- see
`docs/RESEARCH_AGENT.md` for exactly why that line was not crossed.

## Also fixed this pass, raised by you directly

The local generation length caps (64/96/128 tokens depending on backend)
that were cutting replies off after a few lines were real, not imagined --
raised to 256/320/400 tokens with matching context/timeout increases,
committed separately as `68c9340` before this phase's work began. Full
explanation already given in chat; not re-litigated here.

## Milestones D-H: not started this pass, and exactly why

| Milestone | Status | Doc |
| --- | --- | --- |
| D -- Problem solving / coding agent improvements | Not started | `docs/PROBLEM_SOLVING.md` |
| E -- Local knowledge base / RAG | Not started | `docs/RAG_ARCHITECTURE.md` |
| F -- NEXORA Core training (instruction/tool-use) | Not started | `docs/NEXORA_CORE_PROGRESS.md`, `docs/TOOL_USE_TRAINING.md` |
| G -- Full evaluation/regression suite expansion | Not started beyond the Phase 6 note added to `docs/AGENT_EVALUATION.md` | same file |
| H -- Chat UI upgrades (streaming indicators, citation display, approval dialogs, etc.) | Not started | see below |

Each of those docs states the actual reason (not a generic "ran out of
time"): in every case, either the prerequisite work from an earlier
phase (loss masking for training, a unified verification shape for
problem-solving) doesn't exist yet, or starting it now would mean three
half-finished subsystems instead of one finished one -- which Phase 6's
own instructions explicitly says not to do.

### On the UI specifically

No frontend changes were made this pass. The new `/api/search`,
`/api/browser/*` and `/api/research/ask` endpoints are real and callable
today (by any client, including a future chat UI), but no chat-interface
wiring (search activity indicators, clickable citations, streaming,
approval dialogs) was built. This needs its own scoped pass against the
actual frontend code, not a guess at what "ChatGPT-style" means without
reading the existing `frontend/` implementation first.

## Testing

```
PYTHONPATH=. .venv/bin/python -m pytest -q
62 passed
```

37 tests from before Phase 5, plus 9 (Phase 5 NVIDIA/eval), plus 16 new
this pass (6 search, 6 browser, 4 research agent). `ruff check`/`ruff
format` clean on every new/changed file.

## Acceptance tests (Phase 6 §19), actual results

| # | Test | Result | Evidence |
| --- | --- | --- | --- |
| 1 | NEXORA starts locally | **Pass** | Live `TestClient` app construction this pass and Phase 5 |
| 2 | A real local model responds in chat | **Pass** | Covered by the existing passing cowork/reference tests |
| 3 | Search integration returns live results | **Pass** | Live, not mocked, shown above and in `docs/WEB_SEARCH_INTEGRATION.md` |
| 4 | Browser automation opens a public page | **Pass** | Live Wikipedia navigation, this pass |
| 5 | Extracted content is stored with provenance | **Pass** | `artifacts/search-evidence/`, `artifacts/research-evidence/`, each hashed and timestamped |
| 6 | Research answers include real citations | **Pass** | 3 real citations, real URLs, shown above |
| 7 | Invalid or unavailable sources are handled correctly | **Pass** | Unknown-provider 422, read-failure recorded not swallowed, no-sources-found reported explicitly -- all tested |
| 8 | The agent solves a programming task | **Partial** | Demonstrated in Phase 5 (SmolLM2 wrote a correct `add_numbers` function); not re-demonstrated this pass since Milestone D (coding agent) wasn't started |
| 9 | The coding solution passes actual tests | **Partial** | Same Phase 5 evidence: real sandbox execution, exit 0, correct output |
| 10 | Tool permissions are enforced | **Pass** | SSRF guard, scheme allowlist, provider allowlist, all tested this pass; sandbox permission tests from Phase 4/5 still pass |
| 11 | Conversation history persists | **Pass** | Unchanged, still covered by `tests/test_cowork.py` |
| 12 | The local knowledge base answers questions from an ingested document | **Blocked** | Milestone E (RAG) not started -- no knowledge base exists yet |
| 13 | NEXORA Core loads independently | **Pass** | Unchanged from Phase 5's independent reproduction |
| 14 | At least one bounded training experiment completes | **Not attempted this pass** | Phase 5 already has one (`phase5-instruction-pilot-v1`); Milestone F wasn't started this pass, so none is new |
| 15 | Evaluation compares the new checkpoint with the baseline | **N/A this pass** | No new checkpoint this pass; Phase 5's comparison stands |
| 16 | No credentials appear in Git | **Pass** | Diff/grep-scanned before every commit this pass, same as every prior phase |
| 17 | The frontend build and backend tests pass | **Pass** | Backend: 62/62. Frontend: actually re-run this pass -- `npm run typecheck` (clean) and `npm run build` (compiled successfully, 4 static pages generated) both passed, even though no frontend files were touched |
| 18 | Verified code is committed and pushed to GitHub if authorized | **Pass** | See below |

## GitHub

Commits from this pass pushed to `research/phase2-model-reliability` using
the SSH credential already authorized in Phase 4. `main` untouched, no
force-push.
