# Isolated computer-use profile

Phase 8 implements browser tasks, not general desktop control. `/api/computer`
creates a durable plan, requires its exact SHA-256 approval, spawns a worker,
records per-step observations, verifies visible text and saves a hashed PNG.
The Browser workspace exposes plan review, approval, progress, cancellation,
history and screenshot inspection.

Profiles:

- `fixture`: fixed `http://127.0.0.1:8000/api/computer/fixture`; type a test display
  value, click its Preview button, assert the greeting and capture a screenshot.
- `public-read`: public HTTP(S) URL plus expected visible text; navigate, inspect,
  assert and screenshot. No clicking/typing/scripts on arbitrary public pages.

A fresh Chromium context has no personal profile, cookies, saved credentials,
permissions or persistent browser storage. Downloads/popups are blocked. Only
GET document requests pass the route guard; redirects and frames are checked.
Private addresses and credentials in public URLs are rejected. The fixture
exception is its exact URL, not all localhost services. This is a basic DNS/IP
guard, not a hardened anti-DNS-rebinding proxy or network-namespace sandbox.
Chromium runs as the current user, with its normal sandbox; OS cgroups do not cap
this worker's browser descendants. Measured RSS and low-available-RAM checks are
not equivalent to a hard memory limit.

Fixed plans contain dependencies and five-second action timeouts, a 35-second
cooperative task deadline and at most two approved attempts. Failures/interrupted
workers may be replayed only after exact-plan approval, from a new browser;
prior DOM state is never assumed. Cancel markers are checked between actions.
Worker PID creation time detects stale PIDs; a live worker can continue across
an API restart. Events and evidence persist under `artifacts/computer-tasks/`.

Login, private uploads, messages, publishing, purchasing, deletion, privileged
commands and system settings are unsupported. No approval can enable those
operations through this profile. A broader profile requires a separate reviewed
implementation. Page text never changes the fixed plan or tool permissions.

Demo: `.venv/bin/python scripts/phase8-browser-demo.py` on an unused disposable
fixture. It rejects an incorrect plan hash, then explicitly approves its own
fixture plan. `docs/evidence/phase8/computer-demo.json` and `computer-demo.png`
record the real run. DOM assertion is the automated completion criterion; the
screenshot is retained and was visually inspected, not classified by a model.
