# Phase 6 — initial audit

Run 2026-10-18, same day as the Phase 5 audit, so this is deliberately
short where nothing changed and focused where something did. Full prior
detail: `docs/phase5-system-audit.md`.

## Unchanged since Phase 5 (re-confirmed, not re-derived from scratch)

- Git: `research/phase2-model-reliability` at a clean working tree,
  tracking `origin` via the already-authorized SSH credential.
- Tests: 46/46 passing before this pass's changes (now 62/62 after adding
  the modules below -- see `docs/PHASE6_DELIVERY.md`).
- Hardware: still 7.5 GiB total RAM (`free -h` and the API's own `psutil`
  check agree, a fourth independent confirmation across two days of
  sessions), no NVIDIA GPU, Intel Iris Xe only. **The 32 GB figure remains
  wrong for this machine.**
- Provider registry: NEXORA Core, Ollama/SmolLM2, LocalAI, FCC, NVIDIA NIM
  (model discovery live-verified, 81 catalog models, no key), plus six
  documentation-only hosted entries -- unchanged from Phase 4/5.
- MCP: the workspace MCP server (`nexora.cowork_mcp`) is unchanged and
  still exercised by `tests/test_cowork.py::test_real_stdio_mcp`.

## What changed since Phase 5: the NVIDIA reference download

The 2.8 GB NVIDIA Nemotron-3-Nano-4B download that was in progress during
the Phase 5 audit (started independently of any session, not by this
project's own automation) **failed partway through**, at 2.3 of 2.78 GB,
with `urllib.error.URLError: [Errno -3] Temporary failure in name
resolution` -- a DNS resolution failure against `huggingface.co`, not a
content or auth error. No `artifacts/nvidia-download.json` was written
(it is only written on full success), so this download did not complete
and nothing changed in `artifacts/reference-models/nvidia/` (still empty).
This is evidence of real network flakiness in this environment, not
assumed -- directly relevant to §2 below.

## Network connectivity -- checked properly this time, host and API-equivalent paths

Section 1 of the Phase 6 prompt specifically asks to check connectivity
"from both the host and the agent runtime." What was actually checked:

| Target | Reachable from this Bash shell (same network namespace the NEXORA API process runs in) |
| --- | --- |
| `github.com`, `api.github.com` | Yes (used for the git push already) |
| `integrate.api.nvidia.com` | Yes (confirmed again, consistent with Phase 4/5) |
| `build.nvidia.com` (the marketing/catalog website, a different host) | **No** -- consistent failure across three sessions |
| `1.1.1.1` (raw IP, no DNS) | No -- `403 Forbidden`, suggesting a filtering layer, not pure DNS failure, for some destinations |
| `huggingface.co` | Intermittently -- the in-progress download above reached it for 2.3 GB then failed with DNS resolution error |
| `en.wikipedia.org`, `export.arxiv.org`, `api.crossref.org`, `api.github.com/search` | **Yes, all four, live-verified this pass** -- see `docs/WEB_SEARCH_INTEGRATION.md` |

**Conclusion**: this is not a simple "network on/off" environment. Some
hosts work reliably, some fail reliably (`build.nvidia.com`), and at least
one (`huggingface.co`) is intermittent. Any code that makes outbound
requests from this environment -- the new search and browser modules
included -- must assume failures will happen and handle them with
retries and explicit error reporting, not silent success. This is exactly
how `nexora/search.py` was built (see that doc).

## Browser automation -- a real capability that existed but was unverified for live web reading

Playwright's Python package was already a dependency, and Chromium
binaries were already installed system-wide at `/var/cache/ms-playwright`
(not the usual user cache path) from earlier `scripts/browser_qa.py` work.
This pass is the first time it was used to read a **live external page**
rather than the local NEXORA UI -- confirmed working this session (see
`docs/BROWSER_AUTOMATION.md`).

## API keys -- checked without printing them

`env | grep -iE "key|token|search|brave|tavily|exa|serper|bing|google"`
found no search-provider credential of any kind (`BRAVE_API_KEY`,
`TAVILY_API_KEY`, `EXA_API_KEY`, `SERPER_API_KEY`, `GOOGLE_CSE_KEY`,
`BING_SEARCH_KEY` -- none set). `NVIDIA_NIM_API_KEY` remains unset, same as
every prior phase. No key was printed; only its presence/absence was
checked, consistent with this project's existing policy.

## What this means for Phase 6's execution order

Milestone B (one real search provider + browser reader) does not need a
credential at all -- Wikipedia, arXiv, Crossref and GitHub search are all
live-verified reachable with zero keys. That is what this pass built;
see `docs/PHASE6_DELIVERY.md` for the full milestone-by-milestone result.
