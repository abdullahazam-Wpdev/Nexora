# Web search integration — Phase 6

Module: `nexora/search.py`, mounted at `/api/search` and `/api/search/health`.
Tests: `tests/test_search.py` (6 tests, mocked HTTP, no live calls in CI).

## What is implemented and live-verified (2026-10-18, zero cost, no key)

| Provider | Endpoint | Key needed | Verified live this pass |
| --- | --- | --- | --- |
| Wikipedia / MediaWiki | `en.wikipedia.org/w/api.php` (`list=search`) | No | Yes -- real results for "python programming language" |
| arXiv | `export.arxiv.org/api/query` (Atom XML) | No | Yes -- real paper titles/abstracts for "transformer attention mechanism" |
| Crossref | `api.crossref.org/works` | No | Yes |
| GitHub code/repo search | `api.github.com/search/repositories` | No (unauthenticated, rate-limited) | Yes -- real repos for "nexora" |

**A real finding, not assumed**: Wikipedia's API returned `403 Forbidden`
on the first attempt, with a default HTTP client user agent. Per
Wikipedia's own published etiquette
(https://www.mediawiki.org/wiki/API:Etiquette, already cited elsewhere in
this project), it requires a descriptive `User-Agent` identifying the
application. Adding one (`nexora.search.USER_AGENT`) fixed it immediately,
confirmed by a second live call. This is recorded here because it is
exactly the kind of real integration problem a shallow implementation
would miss.

## Not implemented, and exactly why

Brave, Tavily, Exa, Serper, Google Programmable Search, and Bing-compatible
search are all requested by Phase 6 but **not implemented**, because no
credential for any of them exists anywhere in this environment (checked
via `env`, never hardcoded, never printed). `nexora.search.NOT_IMPLEMENTED_NO_KEY`
names each one and the environment variable it would need
(`BRAVE_API_KEY`, `TAVILY_API_KEY`, `EXA_API_KEY`, `SERPER_API_KEY`,
`GOOGLE_CSE_KEY`, `BING_SEARCH_KEY`) so `/api/search/health` reports them
honestly rather than omitting them silently. Writing an adapter for a
service with no key to test it against would be unverifiable, untested
code -- exactly what this project's own rules say not to do. Get any one
of these keys and tell me which, and I will add and live-test that
adapter next.

## Interface

```python
from nexora.search import search
result = search("query text", providers=["wikipedia", "arxiv"], limit=5)
# {"query": ..., "results": [...], "errors": {...}}
```

Each result in `results` is normalized to exactly the fields Phase 6
asked for: `title`, `url`, `snippet`, `publisher`, `published_at` (when
the provider has one), `retrieved_at`, `provider`, `relevance` (a
provider-specific dict -- rank, score, stars, word count, etc.),
`content_hash` (sha256 of url+snippet, for later integrity checking by
the research agent).

## Reliability features implemented

- **Timeouts**: 10s per request.
- **Retries**: up to 2 retries with backoff on transient HTTP/network
  errors (the `_get` helper; arXiv's XML path retries independently since
  it isn't JSON).
- **Error handling**: a failing provider never raises past `search()` --
  it's recorded in the returned `errors` dict, and the other providers'
  results are still returned. Verified by
  `test_search_one_provider_failure_does_not_sink_others`.
- **Deduplication**: exact URL match across providers.
- **Caching**: 5-minute in-memory cache per (query, providers, limit) key,
  verified by a test that counts actual calls.
- **Health checks**: `GET /api/search/health` performs one real, cheap
  call per implemented provider and reports `reachable` or the specific
  error -- it does not just check "is there code for this provider."
- **Ranking**: each provider's own natural rank/score is preserved in
  `relevance`; no cross-provider re-ranking is implemented yet (a
  reasonable next step once more than one provider is typically queried
  at once for the same question).
- **Evidence**: every `/api/search` call writes its full normalized
  result to `artifacts/search-evidence/<hash>.json` and records a summary
  in the audit log.

## Explicitly not claimed

No search here is guaranteed accurate or exhaustive. Wikipedia/arXiv/
Crossref/GitHub each have their own blind spots (Wikipedia skews general-
knowledge, arXiv is preprints only, Crossref is academic metadata only,
GitHub search is code/repos only). A query needing current news, for
example, is not well served by any of these four -- that gap is exactly
what Brave/Tavily/Exa would close, and remains open until a key is
provided.
