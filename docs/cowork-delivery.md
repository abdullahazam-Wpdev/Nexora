# Local cowork and open-source integration delivery

Date: 2026-10-18. Starting commit: `0c1611a` on `research/phase2-model-reliability`. This extends the completed Phase 2/3 research work; it does not claim a new capable foundation model.

## Working application

Chat: http://127.0.0.1:3001. API: http://127.0.0.1:8000/docs. Research dashboard: `/research`. The unrelated application on port 3000 was preserved.

- Persistent SQLite conversations and visible provider labels.
- Bounded chat with the pinned Ollama SmolLM2 135M Q4 reference, Core prediction, LocalAI CPU and the FCC-to-Ollama proxy.
- Selecting a local provider switches the required model runtime, stopping the other engine first. Runtime changes are rejected during training or an active conversation/reference generation. No remote paid fallback.
- Explicit `/help`, `/files`, `/read path`, `/write path` plus newline/content, `/run script.py`, and `/catalog query` commands.
- Writes create new files only in `artifacts/coworkspace`; hidden, absolute, parent-traversal and escaping symlink paths are rejected.
- Python jobs use a pinned rootless Podman Python image, no network, read-only root/workspace, UID 65534, dropped capabilities, no privilege escalation, 96 MiB memory/no swap, half CPU, 32 tasks and a 10-second deadline. API output is capped at 16 KiB. No arbitrary host shell.
- Stdio workspace MCP server with four tools. Registration is explicit; global client settings were not edited.
- Nine validated provider/research skills in `.agents/skills/` and a capabilities comparison with primary references.

This is a single-owner localhost development application. It is not ready for public multi-user hosting. Workspace actions are explicit user commands, not a demonstrated natural-language autonomous coding agent. Chat history is not training data.

## Real inference checks

The same public greeting prompt, “Say hello briefly.”, was sent through live NEXORA chat routes. These timings are end-to-end for that request, not benchmark comparisons or quality scores:

| Route | Observed reply / behavior | Request seconds |
|---|---|---:|
| LocalAI | `Hello!` | 2.5822 |
| FCC → Ollama | Greeting and offer of assistance; external SmolLM2, not Claude | 1.4259 |
| Ollama | Greeting and offer of assistance | 0.9184 |
| Core | Continued the prompt with incoherent file/module-related prose | 0.3649 |

Exact responses: `cowork-live-results.json`. Context/template/generation behavior differs across engines; these are operational smoke checks, not matched performance or instruction-following evaluations. Previous limitations in `reverse-engineering-reference-setup.md` still apply. A hello reply does not demonstrate general reasoning, coding or tool planning.

## Installed runtimes

### LocalAI

- Official binary v4.11.0, 195,276,962 bytes.
- SHA-256 `2211f0c5923db1cb9213006bbc34db1f8cddb68b6342026603d9128997920a74`, checked against GitHub release asset metadata before execution.
- Pinned CPU llama.cpp backend OCI manifest `sha256:cc0eaf6d6db4c5c22b9e431e7d90b917906a2262add102da65f241b4cfe06bf7`.
- Compressed backend layer 50,037,362 bytes, below the separately approved 300 MB backend budget. OCI digest integrity was used; publisher signature verification was not performed and upstream emitted that warning.
- Reuses the already verified 105 MB SmolLM2 GGUF; no duplicate model download.
- Binary `.tools/localai/local-ai`; backend `artifacts/localai/backends/llama-cpp`; model config `artifacts/localai/models/smollm2.yaml`.
- Host user service `nexora-localai`: loopback 8080, 900 MiB memory, no swap, CPU quota 200%, two inference threads, context 512, one active backend, idle/busy watchdogs. Agent/MCP/UI/runtime-settings/gallery endpoints disabled. Galleries do not autoload.
- Observed first inference service memory peak 304,193,536 bytes (~290 MiB); sample is not a worst-case bound. `localai-inference.json` records the actual response.
- Inherited `DEBUG=release` initially prevented CLI parsing; launcher removes that variable. First request before restarting after backend installation failed “backend not found”; restarting discovered the installed backend and real generation passed.

Reproduce after approval for these downloads on a new machine:

```sh
scripts/prepare-localai.sh
scripts/localai.sh version
scripts/localai.sh start
# Stop before starting Ollama manually:
scripts/localai.sh stop
scripts/ollama.sh start
```

The chat selector manages this switch on this Fedora/systemd workstation. `localai.sh` is tailored to this host/Flatpak bridge; it is not a universal operating-system installer.

### Supplied free-claude-code archive

- ZIP SHA-256 `1368b42cecc2cb511c482e0721143e59db7ca0cde93df01f6a33e919187cf267`.
- 1,086 entries: 1,000 file entries and 86 directory entries in the ZIP central directory; REA counts the ZIP itself as one additional file occurrence (1,001), with no symlinks. REA graph has 1,087 nodes including the archive itself. See the exact REA evidence rather than adding these counts without that distinction.
- Uncompressed entry bytes: 12,355,716. No model weights found; large tokenizer vocabulary data is not LLM weights.
- AGPL-3.0-only proxy remains separate from NEXORA Core. No upstream source code was copied into the main Python package; source archive and installed package remain in ignored local directories.
- Exact Python requirement `==3.14.7`; neither Core's Python 3.13 nor host 3.14.8 satisfied it. Installed uv 0.13.1 in the project environment and a separate managed Python 3.14.7 / `.tools/fcc-venv`.
- 103 packages passed the isolated dependency check. `tooling/fcc/requirements.lock` pins installed dependency versions.
- ZIP lacked VCS packaging metadata. A local import Git commit was created within the extracted ignored source. Installed version `0.1.dev1+gdaf031e0f` is local packaging metadata, not an upstream release claim.
- Wrapper redirects FCC's managed-state path helper to `artifacts/fcc-state`, seeds its schema before any legacy migration, disables browser launch, requires an ignored random proxy token, and pins every model tier and fallback setting to local Ollama only. HOME is unchanged. Vendor client launchers/install.sh were not executed.
- First integration attempt incorrectly instantiated the vendor's pure Settings model without its configuration loader, selecting the default NIM provider; it failed without credentials. Corrected to use the managed configuration loader and asserted local routing. No NIM inference succeeded or spending occurred.
- Authenticated `/v1/messages` passed; missing-token requests returned 401. The proxy returns Claude-compatible model *aliases*. NEXORA labels replies as external SmolLM2, never actual Claude.
- Service `nexora-fcc`: localhost 8082, memory cap 384 MiB/no swap, CPU quota 100%, task cap 96. Its upstream code-agent features were not comprehensively audited or enabled in NEXORA's workspace tools.

```sh
.venv/bin/python scripts/install-fcc.py
scripts/ollama.sh start
scripts/fcc.sh start
scripts/fcc.sh status
```

The installer revalidates the supplied archive hash, extraction paths and sizes. It does not modify Claude/Codex client configuration. Local source path: `artifacts/vendor-src/free-claude-code-zip/free-claude-code-main`.

REA static archive inspection was exported to `free-claude-code-rea-evidence.json`. An attempted REA analysis snapshot was unsupported for this archive's profile; no snapshot is claimed. The target was closed normally after exporting evidence. Static inventory does not prove runtime safety or model capabilities.

## Data and actual training

Pinned source: LocalAI revision `0d6e57f9f5f2b666396a87d7062c80c9647ec483`, MIT notice retained. Six document source groups; repository authorship was not independently established. No claim that the source is exclusively human-authored. No proprietary platform conversations, books, private browser data or teacher outputs were ingested.

- Dataset `localai-docs-pilot-5bbfc531d2a3`.
- 59 input paragraphs, 58 accepted, one exact duplicate rejected.
- 39 train / 7 validation / 12 test documents, with source-level separation and zero exact overlap. Existing near-duplicate filtering threshold 0.85.
- Token streams: 4,694 train / 1,146 validation / 1,202 test; held-out loss uses 1,145 and 1,201 prediction targets respectively.
- Run `localai-docs-pilot-8`: 172,352 parameters; eight real CPU optimizer steps; 1,024 training tokens.
- Validation loss **6.7838461530**; validation perplexity **883.4601208**.
- Test loss **6.7995608772**; test perplexity **897.4531130**, independently checked as `exp(test_loss)`.
- Engine session wall 0.5548 seconds, peak process RSS 331.25 MiB, training-only 9,469.75 tokens/second, maximum sampled CPU temperature 55°C. Training-only throughput excludes data/checkpoint/evaluation overhead and is a tiny-run observation, not a sustained scaling estimate.
- Separate checkpoint: `artifacts/runs/localai-docs-pilot-8/checkpoints/step-0000008/`; manifest/tokenizer/result files remain with the run and dataset. Full exact measurements: `cowork-pilot-results.json`.

This pilot is undertrained and unsuitable as an assistant. Its perplexity cannot be compared numerically with the earlier Core result because dataset and tokenizer differ. It was not promoted. The selected model remains `phase2-small-language`, and its step-400 model SHA-256 remains `0b10d349fe2a8517544cd31cee03140eba7aa730fd1087ae01f0b02b1b56ee84`.

Reproduce a fresh bounded run (choose an unused ID; existing runs are never overwritten):

```sh
.venv/bin/python scripts/train-documentation-pilot.py --run-id localai-docs-reproduce
```

## Daily discovery and catalogs

`catalogs/manifest.json` records pinned revisions and README/LICENSE hashes for public-apis and awesome-free-models; notices are retained. They are references, not a license grant to the APIs/models they list. No bulk endpoint calls, model installs or cloud resources were provisioned.

`nexora-learning.timer` is installed in the user's systemd instance at 09:00 Asia/Karachi, with a two-minute randomized delay and missed-run recovery. It launches a standard-library host-Python discovery script, so the host/Core Python ABI mismatch does not matter. The service has a 60-second timeout, CPU quota 50% and 256 MiB memory limit. Only three public repository revision endpoints are fetched in series, up to 256 KiB each. Manual and real systemd service runs succeeded. Candidates stay unapproved; there is no unattended training or weight promotion.

```sh
.venv/bin/python scripts/learning-cycle.py
scripts/install-learning-timer.sh
flatpak-spawn --host systemctl --user list-timers nexora-learning.timer
flatpak-spawn --host systemctl --user disable --now nexora-learning.timer
```

Unit files live in the Flatpak-visible user config systemd directory and are explicitly linked into the host user systemd directory by the installer. No system-wide dependencies were installed. Vercel, Drive and CDN provisioning were unnecessary for available local storage. Wikipedia/blog/book licenses require an item-specific policy before ingestion; no full dump or copyrighted book collection was downloaded.

## Verification

- Python suite: **37 tests passed**; includes conversation persistence across app recreation and an actual live API process restart, workspace boundaries/symlinks, overwrite protection, sidecar failure without silent fallback, and real stdio MCP initialization/list/create/read.
- Ruff F checks passed across package/scripts/tests; Core and FCC dependency checks passed.
- Frontend TypeScript and production build passed, including `/` and `/research` routes.
- Playwright desktop/mobile, local reply, command, persisted reload and model-selector runtime checks passed; screenshots in `artifacts/cowork-verification/`.
- Live API integration verified all four provider paths and blocked an untrusted browser mutation origin.
- Sandbox: UID 65534, correct arithmetic result, network blocked, workspace writes blocked, infinite-loop timeout ~10.15 seconds, and no remaining task containers. Exact evidence: `cowork-sandbox-results.json`.
- Original selected Core checkpoint hash checked unchanged.

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check nexora scripts tests --select F
.venv/bin/python scripts/verify-cowork-live.py
.venv/bin/python scripts/verify-cowork-sandbox.py
.venv/bin/python scripts/cowork-browser-qa.py
export PATH="$PWD/.tools/node/bin:$PATH"
(cd frontend && npm run typecheck && npm run build)
```

## GitHub and remaining work

Requested remote `origin` is configured as `https://github.com/abdullahazam-Wpdev/Nexora.git`; repository-local author/email match the user's supplied identity. Git cannot authenticate, and the GitHub integration is not yet connected. No push is claimed. Never paste tokens into chat or commit them. After authentication, inspect remote refs/history before publishing the research branch; do not force-overwrite the remote default branch.

The platform does not replicate proprietary foundation models, provide every catalog API automatically, or demonstrate autonomous multi-agent coding. Hosted providers are researched skills/documentation, not connected paid accounts. Next meaningful milestone: rights-reviewed corpus expansion with stable evaluation and a measured stronger instruction-following reference, followed by tool-selection and patch-review benchmarks before autonomous execution.
