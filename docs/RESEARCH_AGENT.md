# Research agent — Phase 6

Module: `nexora/research_agent.py`, mounted at `POST /api/research/ask`.
Tests: `tests/test_research_agent.py` (4 tests, mocked search/browser
layers so CI doesn't depend on live network).

## The real pipeline implemented

```
question -> nexora.search.search() [live, real]
         -> nexora.browser_reader.read_url() on top sources [live, real]
         -> extractive citation assembly [real, no model involved]
         -> evidence file written to artifacts/research-evidence/<id>.json
```

Live-verified this pass with the real question "Guido van Rossum Python
creator": returned 3 real Wikipedia citations, each with a real URL, a
real retrieval timestamp, and a real excerpt read from the live page
(after fixing the content-extraction bug described in
`docs/BROWSER_AUTOMATION.md`), and wrote a real evidence file.

## What "answer" actually is -- read this before trusting it

The `answer` field is an **extractive summary**: the strongest excerpt
from each citation, concatenated and labeled `[c1]`, `[c2]`, etc. It is
**not** fluent, model-composed prose, and the response explicitly labels
this (`answer_kind: "extractive_summary_of_retrieved_sources,_not_model_generated_prose"`).

This is a deliberate, stated limitation, not an oversight: NEXORA Core and
the local Ollama/SmolLM2 reference have both been measured this project
(`docs/AGENT_EVALUATION.md`) to fail basic instruction-following and
coherent generation. Having either of them "write up" the retrieved
evidence into a polished answer would risk the model silently dropping,
garbling, or contradicting the actual sources while sounding fluent --
exactly the failure mode Phase 6 §5 prohibits ("Do not present model-
generated guesses as verified facts"). Shipping a correct-but-unpolished
extractive answer is the honest choice until a capable enough model is
connected (NVIDIA NIM, once a key is configured) to draft from the
citations without misrepresenting them -- that wiring is the next step,
not done this pass.

## Evidence and citation fields (Phase 6 §5 checklist)

Each citation includes: source URL, page title, retrieval time
(`retrieved_at`), publisher, the actual extracted text
(`full_text_excerpt`, from a real page read, not invented), a content
hash, a citation identifier (`c1`, `c2`, ...), and `read_status` (`read`,
`not_attempted`, or `failed: <reason>`). Reliability indicators are
currently limited to `provider` and the raw relevance metadata from
`nexora.search`; a dedicated trust/reliability score is not implemented.

## Honesty behaviors, verified by test

- **No sources found → reported, not hidden**: `status: "no_sources_found"`
  with the actual search errors attached, `answer: null`. Tested.
- **A source that fails to load → recorded, not silently dropped**: the
  citation's `read_status` becomes `failed: <the real exception message>`,
  and the pipeline falls back to the search snippet rather than fabricating
  page content. Tested.
- **Unknown provider name → rejected (422)**, not silently ignored. Tested.

## Distinguishing verified / inferred / unknown (Phase 6 §5)

Partially implemented: every citation's `full_text_excerpt` is verified-
from-source (it is literally the retrieved text). There is not yet a
per-sentence classification into verified/calculated/inferred/unverified/
unknown within the extractive answer -- that requires either a capable
model to do the classification or substantial rule-based NLP, neither of
which this pass built. Today, the whole answer carries one honest label
(`extractive_summary_of_retrieved_sources`) rather than a false claim of
finer-grained verification.

## What this pipeline does not cover yet (Phase 6 §4 categories)

Tested and working for general factual/technical questions where
Wikipedia/arXiv/Crossref/GitHub have coverage (the audit's example:
Python/Guido van Rossum). **Not specifically built or tested**: WordPress
development, Shopify development, or SEO research -- none of the four
implemented providers specialize in those, and no additional provider was
added for them this pass (would likely need a general web-search API like
Brave/Tavily, which need a credential not present here).

## Contradiction handling (Phase 6 §4)

Not implemented. With only one provider typically queried per question and
an extractive (non-synthesizing) answer, there is no cross-source
reconciliation step yet. Querying multiple providers for the same question
and comparing their citations is possible today via the existing
`providers` parameter, but nothing automatically flags disagreement.
