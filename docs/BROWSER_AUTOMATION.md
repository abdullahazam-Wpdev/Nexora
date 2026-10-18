# Browser automation and web reading — Phase 6

Module: `nexora/browser_reader.py`, mounted at `/api/browser/read` and
`/api/browser/find`. Tests: `tests/test_browser_reader.py` (6 tests; the
SSRF-guard test runs real DNS/IP-range checks, the endpoint tests mock the
actual browser launch to stay fast and offline-safe in CI).

## What is implemented and live-verified this session

Using Playwright + Chromium, already installed at `/var/cache/ms-playwright`
from earlier project work:

- **Open URL / navigate**: real headless Chromium navigation, confirmed
  against `https://en.wikipedia.org/wiki/Python_(programming_language)`.
- **Read visible page text**: extracts from the actual content container
  (`#mw-content-text`, `article`, `main`, or `#content`, falling back to
  `<body>`), not raw `<body>` text, which on most sites (confirmed on
  Wikipedia) is mostly navigation chrome before any real content. This
  was caught and fixed during this pass, not assumed correct.
- **Extract headings and links**: real `h1`/`h2`/`h3` text and `<a href>`
  links, bounded to 30 headings / 40 links.
- **Search within a page**: `find_in_page(url, phrase)` returns up to 10
  matches with 80 characters of surrounding context each -- confirmed
  live, finding "Guido van Rossum" in the Python Wikipedia article with
  correct context.
- **Capture screenshots**: optional, saved to
  `artifacts/browser-evidence/<timestamp>.png`.
- **Handle browser errors**: navigation failures are caught and reported
  as a specific message, not a crash.
- **Close sessions cleanly**: `browser.close()` in a `finally` block,
  always runs even on navigation failure.
- **Bounded navigation**: 15-second navigation timeout, 20,000-character
  text cap (`truncated: true` when hit), 40-link cap.

## Isolation and safety, verified not just claimed

- **No profile, no cookies, no passwords**: every call launches a brand
  new headless browser context from scratch. There is no persistent
  profile directory and no code path that could reach the owner's real
  browser's saved data -- there's nothing shared to isolate *from*,
  which is a stronger guarantee than sandboxing a shared profile would be.
- **Scheme allowlist**: only `http`/`https` accepted; `file://`,
  `javascript:`, `ftp://`, etc. rejected before any browser launches.
  Verified by `test_validate_url_rejects_private_and_non_http`.
- **SSRF guard**: the target hostname is resolved and every returned IP is
  checked against private/loopback/link-local/reserved/multicast ranges
  (via Python's `ipaddress` module) before navigation. Verified live
  against `127.0.0.1`, `localhost`, and `169.254.169.254` (the cloud
  metadata-service address many SSRF exploits target) -- all three
  correctly rejected.
- **Authenticated sites**: out of scope by construction. There is no
  login flow, no credential input, and no session persistence across
  calls, so there is nothing to allowlist yet -- a future addition would
  need an explicit per-site approval step before adding one.
- **One session at a time**: a lock bounds concurrent Chromium instances
  to one, protecting the 7.5 GiB RAM budget measured in
  `docs/phase6-initial-audit.md`.
- **Content is data, not instructions**: stated explicitly in the module
  docstring and enforced by how the research agent consumes it (see
  `docs/RESEARCH_AGENT.md`) -- page text is never passed anywhere that
  would let it act as a command to this agent.

## Not implemented this pass

- **Following relevant links automatically**: `read_url` returns the link
  list; the research agent does not yet follow any of them itself (it
  only reads the top search results). Automatic link-following is a
  real scope increase (crawl depth limits, loop detection) better done as
  its own change.
- **An allowlist mechanism for authenticated sites**: not needed yet since
  no authenticated flow exists; would be designed when a concrete use
  case needs it rather than speculatively now.
