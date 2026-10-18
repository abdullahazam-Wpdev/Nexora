# Free Claude Code integration — current state

This integration already exists from an earlier phase. This document records
its current, re-verified state rather than re-doing the install. The
authoritative review and evidence are in
[reverse-engineering-reference-setup.md](reverse-engineering-reference-setup.md),
[integrations.md](integrations.md), [provider-capabilities.md](provider-capabilities.md)
and the README's "Open-source integrations" section.

## What is actually installed

- Source: https://github.com/alishahryar1/free-claude-code, AGPL-3.0. The
  supplied archive contains tokenizer data, not model weights.
- Installed in an isolated Python 3.14.7 virtual environment
  (`.tools/fcc-venv`), with dependency locks retained under
  `tooling/fcc/requirements.lock`. It was **not** installed over NEXORA
  source, and its global client auto-configuration installer was **not** run.
- `scripts/fcc-sidecar.py` starts FCC's own unmodified ASGI app with
  project-local state (`artifacts/fcc-state`), binds `127.0.0.1:8082` only,
  requires a locally generated, file-stored bearer token
  (`.secrets/fcc-token`, mode 0600) via `PROXY_AUTH_ENABLED=true`, and hard-fails
  (`SystemExit`) if its resolved model config points anywhere other than the
  local pinned Ollama SmolLM2 model -- so it cannot silently start with a
  paid/remote provider.
- `scripts/fcc.sh {start|stop|status}` runs that sidecar as a resource-capped
  user systemd unit (384 MiB memory cap, no swap, 1 CPU, 96 tasks).

Routing today is **FCC → local Ollama only**. It is a coding-client-to-API
translation proxy, not a source of Claude model weights, and not an unlimited
subscription. `docs/fcc-inference.json` records one real local round trip
through it (model label `claude-haiku-4-5` is FCC's own internal routing
name for the request; the actual inference ran on the local SmolLM2 model).

## About the commands named in the Phase 4 prompt

The prompt that triggered this work mentions `fcc-server`, `fcc-codex` and
`fcc-claude` as commands. **These do not exist in this repository** -- they
were not defined by the earlier FCC install and were not added now, because
inventing shell aliases to match assumed command names without verifying what
they should do would misrepresent what is actually wired up. The real,
tested commands are:

```sh
scripts/fcc.sh start    # start the local sidecar (FCC -> Ollama only)
scripts/fcc.sh status   # check it
scripts/fcc.sh stop     # stop it
```

If you want `fcc-server`/`fcc-codex`/`fcc-claude` as named entry points (e.g.
to launch a coding harness like Codex CLI or Claude Code pointed at this
proxy), that is a small, separate, well-scoped addition -- tell me which
harness binaries you have installed and I will wire real wrapper scripts
rather than guessing their flags.

## Security review boundary (unchanged from the earlier phase)

- Binds loopback only; proxy requires the local bearer token.
- Does not modify global Codex/Claude Code settings.
- Does not send requests to any third party beyond the local Ollama runtime.
- Not a sandbox for arbitrary code; it is a request-translation proxy only.

## Re-verification this session

`scripts/fcc.sh status` was not re-run in this pass beyond reading its source
(see [PHASE4_VERIFICATION.md](PHASE4_VERIFICATION.md) for which acceptance
tests were actually executed this session vs. relied on prior evidence).
