# NVIDIA speech, model catalogs and optional memory

Implemented 2026-10-18. No model weights were added. No paid account or hosted
inference call was provisioned. These integrations do not train NEXORA Core.

## Riva / Whisper Large V3

The project-local `.venv` now has `nvidia-riva-client==2.27.0`; the upstream MIT
Python clients are cloned under `.tools/riva-python-clients`, pinned in
`tooling/riva/installation.json`. Reproduce without system-wide installation:

```sh
.venv/bin/python -m pip install '.[speech]'
git clone https://github.com/nvidia-riva/python-clients.git .tools/riva-python-clients
git -C .tools/riva-python-clients checkout 54749aa2ff39a07f78e02c6525b7409bd2fe6ade
.venv/bin/python .tools/riva-python-clients/scripts/asr/transcribe_file_offline.py --help
```

Use **Whisper speech** in NEXORA, enable NVIDIA hosted Riva, choose language
(`en`, `fr`, or `multi`) and transcription or translation to English, then
explicitly approve sending audio. The server needs `NVIDIA_API_KEY` or
`NVIDIA_NIM_API_KEY` in its environment and must be restarted after setting it.
The UI disables hosted submission until the client and key are configured.
No key is shipped; hosted transcription/translation remains unverified.

`POST /api/speech/riva/transcribe` takes `wav_base64`, `language`, `task`
(`transcribe` or `translate`) and `allow_hosted: true`. It accepts 16-bit mono
PCM WAV, 8–48 kHz, at most 30 seconds and 2 MB. It sends PCM via TLS gRPC to
`grpc.nvcf.nvidia.com:443`, function ID
`b702f636-f60c-4a3d-a6f4-f3568c13bd7d`. Translation uses custom configuration
`task:translate`; source-language `fr` matches the supplied French example.
Recognition has a 30-second deadline and closes its channel. Errors report gRPC
status only; audio and credentials are not logged, retained or used for training.
The optional local HTTP Speech NIM route remains separate.

The official [Whisper example](https://build.nvidia.com/openai/whisper-large-v3/api)
confirms these connection settings. Its word “offline” means whole-file
recognition; this hosted endpoint still sends audio over the network. The UI
supports WAV only, even though upstream clients support additional formats.

## Gemma, Kimi and retired DeepSeek

The chat model selector includes `google/gemma-7b` and `moonshotai/kimi-k3`
through the existing NIM adapter and explicit hosted-consent checkbox. Both
remain unverified for generation without an account key. Chat requests are
bounded to 1,024 output tokens in the UI and 4,096 through the general NIM API.
We did not install the generated `@api/nim` JavaScript wrapper: the existing
server-side HTTP adapter already implements this API, keeping keys out of the
browser. The sample `nim.auth('34')` is not a valid configured credential.

Kimi's [model card](https://docs.api.nvidia.com/nim/reference/moonshotai-kimi-k3)
requires preserving complete assistant reasoning/tool messages for multi-turn
use. NEXORA therefore invokes it as **single-turn text only**, without prior
conversation messages. Images, tools and preserved reasoning history are not
implemented for this route. Project notes, if explicitly enabled, are a bounded
reference context. No full-context or coding-benchmark claims are made.

[Gemma's reference](https://docs.api.nvidia.com/nim/reference/google-gemma-7b)
documents the text model; applicable model and hosted-service terms still apply.
The owner-supplied 410 response reports `deepseek-ai/deepseek-v4-flash` retired
on 2026-08-07. It appears in the catalog as unavailable and is not selectable.
Upstream HTTP 410 is propagated with a clear retirement message, with no silent
model substitution. The supplied 16,384-token sample is not enabled on this
bounded laptop setup.

## FCC catalog and routing

FCC is already installed separately in `.tools/fcc-venv`; its upstream AGPL
implementation remains separate from the NEXORA source. The public metadata
snapshot `catalogs/fcc/catalog.json` includes **all 60 provider descriptors and
all eight Claude aliases present in that installed version**. It is extracted
using AST, without importing settings or reading credentials:

```sh
.venv/bin/python scripts/snapshot-fcc-catalog.py
curl --fail http://127.0.0.1:8000/api/models/catalog
```

The **Models** panel displays this snapshot and the live local FCC catalog.
The local FCC `/admin/api/models` discovery currently returns only
`ollama/smollm2:135m-instruct-q4_K_M`. The newer upstream README advertises 61
providers; that differs from the installed snapshot's 60. We did not replace
the working installation or assume those providers are configured.

Selecting FCC in Chat exposes all eight installed Claude routing aliases.
Every alias is deliberately mapped to the pinned local SmolLM2, including
Fable, Opus, Sonnet and Haiku names. This does **not** provide Claude weights
or real Anthropic inference. Remote FCC providers require their own credentials
and reviewed routing changes; the project launcher continues to enforce local
Ollama routing with no remote fallback. There is no finite offline list of all
models across every provider: live catalogs depend on credentials, deployment
and provider changes. The model catalog clearly separates aliases, supported
providers, and currently configured upstream models.

## Memory

The Library already supports persistent owner notes, search, corrections via
API, deletion and expiry. Chat now offers **Use latest local project notes**,
default off. With this on, it retrieves at most three unexpired project or
preference notes from the selected namespace (`local` in the UI), truncates each
to 250 characters and includes them as untrusted reference data. Proposals and
evaluation notes are excluded. The turn response reports `memory_ids` used.

Notes persist in `artifacts/project-memory.sqlite3`, separate from conversations,
provider settings and training datasets. They can be sent to a hosted model only
when both memory and hosted consent are enabled. Core is still a research text
predictor and does not consume this memory. Notes grant no tool permissions and
do not update neural weights. See [memory architecture](MEMORY_ARCHITECTURE.md).

## Delivery verification

- Full automated suite: 90 passed; `pip check` reported no broken requirements.
- Ruff F checks, TypeScript checks and production Next build passed.
- Real local FCC Fable routing-alias request returned HTTP 200 and final text.
- Live FCC discovery returned one configured SmolLM2 model.
- Headless browser verified catalog search, translation controls, missing-key
  submission guard and eight FCC alias options.
- Riva CLI help runs against the installed package. Real protobuf configuration,
  TLS/function/auth metadata, translation configuration, deadline and channel
  cleanup are tested with the gRPC boundary mocked. No transcript accuracy claim.
- Owner project integration note saved in local memory; notes remain off by
  default in chat.
- Current NVIDIA public model-list refresh failed from this environment; model
  cards alone do not prove current hosted availability or account entitlement.
