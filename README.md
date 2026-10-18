# NEXORA AI OS

A local AI research workspace: build an independent foundation model, compare it honestly with open-weight references, and gradually add useful cowork and coding workflows.

The working application provides persistent chat, local inference, an isolated file workspace, explicit Python execution in a rootless container, public API discovery, a workspace MCP server, and a reproducible CPU training/evaluation engine. It does not yet match Claude Code, Codex or ChatGPT. NEXORA Core is a small text-prediction research model; the external SmolLM2 reference is also limited.

## Run locally

For an existing installation, use the commands below. For a fresh checkout, `scripts/bootstrap.sh` installs the pinned Python dependencies and frontend packages (requires a compatible Python and Node 22+); review its download requirements first. Reference/runtime setup is separate and documented in the delivery report.

```sh
scripts/ollama.sh start
scripts/start-local.sh api
# In another terminal, after building the frontend:
export PATH="$PWD/.tools/node/bin:$PATH"
(cd frontend && npm run build)
scripts/start-local.sh ui
```

Open **http://127.0.0.1:3001**. The API is at http://127.0.0.1:8000/docs and the original model dashboard is at http://127.0.0.1:3001/research. Port 3000 is left available for the other application on this machine. Bind these services to loopback only; this is a single-owner development application, not an authenticated multi-user service.

Select **SmolLM2** for local reference chat or **NEXORA Core** for research text prediction. Provider names remain visible. Conversation history persists in `artifacts/cowork.sqlite3`, survives API restarts, and is not automatically used as training data. Context and generated length are deliberately small to fit this laptop.

## Cowork actions

Enter these commands in chat:

```text
/help
/files
/write hello.py
print("Hello from NEXORA", 6 * 7)
/read hello.py
/run hello.py
/catalog weather
```

`/write` creates new files only; existing work is preserved. Paths stay inside `artifacts/coworkspace/`. `/run` executes Python in a rootless Podman container with networking disabled, a read-only filesystem/workspace, unprivileged user, dropped capabilities, 96 MiB RAM, half a CPU, 32 processes and a 10-second time budget. There is no host shell tool. See the delivery report for image pinning and verification commands. Model-generated prose never silently becomes a command.

These are explicit user-directed actions. Reliable autonomous planning, repository-wide editing and unattended agent creation remain research work. Skills are instructions for an agent, not capabilities automatically learned by a model.

## MCP and provider skills

Run the project MCP server over stdio:

```sh
.venv/bin/python -m nexora.cowork_mcp
```

It exposes `workspace_list`, `workspace_read`, `workspace_create`, and `catalog_search`. Use the absolute interpreter path and repository working directory when registering it in a client. No global Codex, Claude or browser settings are changed automatically.

Provider-specific skills live in `.agents/skills/nexora-*`. [Provider capabilities](docs/provider-capabilities.md) records official documentation, reproducible product patterns, actual integration state, licensing and limitations. OpenAI, Anthropic, DeepSeek, Perplexity, Kimi, Grok and Qoder are not connected without credentials; no paid calls or subscription bypasses are performed. Qoder is separate from DeepSeek.

## Data and our foundation model

```sh
.venv/bin/python scripts/learning-cycle.py
# Once per machine: install a bounded daily revision-discovery timer
scripts/install-learning-timer.sh
# Explicit, separately checkpointed MIT-documentation pilot:
.venv/bin/python scripts/train-documentation-pilot.py --run-id localai-docs-reproduce
```

Daily discovery runs at 09:00 Asia/Karachi and checks three public repositories for new revisions. It does not crawl private sessions, download all Wikipedia, install every catalog entry, or train on unreviewed platform responses. Review new content's license, source provenance, quality, deduplication and held-out contamination before ingestion. The documentation pilot uses six source groups from pinned MIT LocalAI documentation with retained notices, eight training steps and separate checkpoints; its poor perplexity is reported rather than hidden. The existing selected Core checkpoint is preserved.

Research design, checkpoint compatibility and scaling measurements: [Phase 2](docs/phase-2-delivery.md), [Phase 3](docs/phase-3-scaling-report.md), [roadmap](docs/roadmap.md). Consult the actual filenames in `docs/` if following older links.

Phase 4 (NVIDIA NIM, REA, agent capabilities, hardware reality check, and the acceptance-test report) is summarized in [docs/PHASE4_VERIFICATION.md](docs/PHASE4_VERIFICATION.md), which links every individual Phase 4 doc and states exactly what is verified versus blocked.

## Open-source integrations

- Ollama + pinned Apache-2.0 SmolLM2 135M Q4: verified local reference inference.
- REA + Hopper demo: installed for authorized artifact analysis; see [setup evidence](docs/reverse-engineering-reference-setup.md). Source repository inspection uses ordinary source tools.
- LocalAI: separate optional CPU inference engine, reusing the reference GGUF where feasible. See [current delivery report](docs/cowork-delivery.md) for verified state.
- free-claude-code: separately isolated AGPL provider proxy. The supplied ZIP has no LLM weights. Do not merge its code into Core or run its global client auto-configuration installer. See [docs/FREE_CLAUDE_CODE.md](docs/FREE_CLAUDE_CODE.md).
- NVIDIA NIM: hosted OpenAI-compatible provider adapter (`nexora/nvidia_nim.py`, `/api/nvidia/*`). Model discovery is verified live against the real catalog with no key (81 models); chat/streaming/embeddings need your own `NVIDIA_NIM_API_KEY` from https://build.nvidia.com. See [docs/NVIDIA_NIM.md](docs/NVIDIA_NIM.md).
- Rootless Podman supplies container isolation; no extra Docker daemon is needed.
- Attributed `catalogs/public-apis` and `catalogs/awesome-free-models` snapshots are discovery material. Listed APIs have their own licenses, keys, quotas and reliability.
- Vercel, cloud object storage, CDN and Google Drive are not provisioned. Local storage suffices; no money has been spent.

## Verification and development

```sh
.venv/bin/python -m pytest -q
.venv/bin/python scripts/verify-cowork-sandbox.py
.venv/bin/python scripts/cowork-browser-qa.py
export PATH="$PWD/.tools/node/bin:$PATH"
(cd frontend && npm run typecheck && npm run build)
```

Do not commit `.env`, `.secrets`, weights, private conversations, browser profiles, database files or vendor environments. These remain ignored. Public catalog licenses and hashes are retained in `catalogs/manifest.json`.

## Next research milestone

Expand a rights-reviewed corpus with stable held-out evaluations; train matched configurations within measured CPU limits; evaluate memorization and generation quality before any promotion. Add a stronger feasible instruction-tuned reference only after a download/RAM budget is approved, then test bounded tool selection and edit review. A capable independent foundation model requires substantially more data and compute than this laptop pilot.
