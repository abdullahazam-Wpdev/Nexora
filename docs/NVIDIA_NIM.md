# NVIDIA NIM integration

Research and implementation date: 2026-10-18. This documents the hosted NVIDIA
NIM adapter added in `nexora/nvidia_nim.py`, what was verified, and what was not.

## Catalog research

- Model browsing: https://build.nvidia.com/models lists NVIDIA NIM catalog
  entries (model id and a short description per model). It is a human-browsable
  list, not a documented programmatic catalog API -- the page's own pagination
  hints at a backend (`/models?page=2`) but NVIDIA does not publish that as a
  stable contract, so this project does not scrape it. Model discovery instead
  uses the documented, stable `GET /v1/models` endpoint below.
- API reference: https://docs.api.nvidia.com/ and
  https://docs.nvidia.com/nim/large-language-models/latest/api-reference.html
  describe an OpenAI-compatible REST surface.

## Verified API shape

| Item | Value |
| --- | --- |
| Base URL | `https://integrate.api.nvidia.com/v1` |
| Auth | `Authorization: Bearer <key>`; keys are generated at https://build.nvidia.com and start with `nvapi-` |
| Model discovery | `GET /v1/models` |
| Text/chat generation | `POST /v1/chat/completions` (OpenAI-compatible; supports `stream: true`) |
| Embeddings | `POST /v1/embeddings` |

**Known gotcha** (confirmed via the NVIDIA developer forum, not reproduced
locally): a key can successfully call `GET /v1/models` and still receive
`403 Forbidden` on `/v1/chat/completions`. This happens when the owning NVIDIA
account/org has not been granted "Public API Endpoints" hosted-inference
access, separately from whether the key itself is valid. `nexora/nvidia_nim.py`
surfaces this as a distinct, named failure rather than a generic 403.

NVIDIA's catalog spans many providers and modalities (text, embedding, vision,
reasoning, coding, healthcare/climate-specific models). The adapter does not
assume a given model id supports tool calling, vision, or embeddings; the
caller must know the model's own documented capabilities before requesting
that feature.

## What is implemented

`nexora/nvidia_nim.py`, mounted at `/api/nvidia/*`:

- `GET /api/nvidia/status` -- always performs a real `GET /v1/models` call
  (that endpoint needs no key) and reports actual reachability/model count,
  plus whether a key is configured for generation. Confirmed live in this
  pass: `reachable: true, model_count: 81, generation_available: false`.
- `GET /api/nvidia/models` -- cached (5 minute) model id listing; works today,
  with no key, confirmed live.
- `POST /api/nvidia/generate` -- non-streaming chat completion; bounded
  `messages` (≤50) and `max_tokens` (≤2048); optional `tools`/`tool_choice`
  passthrough for models that support function calling.
- `POST /api/nvidia/stream` -- streaming chat completion; parses the
  OpenAI-style `data: {...}` SSE frames and yields plain-text deltas.
- `POST /api/nvidia/embeddings` -- embedding generation.
- Added to `nexora/provider_registry.py` as a `hosted` provider so the model
  selector can list it alongside NEXORA Core, Ollama, LocalAI and FCC.

Error handling distinguishes: missing key (503, before any network call),
`401` invalid key, `403` (auth-ok-but-refused, see gotcha above), `404` unknown
model/endpoint, `429` rate limit, and other `4xx/5xx` with the response body
(truncated) attached.

## What is verified vs. not

- **Verified live, 2026-10-18, zero cost, no key**: `GET /v1/models` is
  NVIDIA's public, unauthenticated catalog endpoint. Calling
  `nexora.nvidia_nim.list_models()` and `GET /api/nvidia/status` through the
  real running API, from this environment, against the real
  `https://integrate.api.nvidia.com`, returned a real **81-model catalog**
  (e.g. `meta/llama2-70b`, `nvidia/nemotron-4-340b-instruct`,
  `mistralai/mixtral-8x22b-v0.1`, `google/gemma-3-12b-it`), with no API key
  configured anywhere. This is a genuine end-to-end result, not a mock.
- **Also verified live**: `POST /v1/chat/completions` without an
  `Authorization` header returns `401` with body
  `Header of type \`authorization\` was missing` -- confirming the
  adapter's "missing/invalid key" error path matches the real API's actual
  behavior, not just an assumption.
- **Not verified live**: actual text generation, streaming, embeddings, and
  tool-calling, because no `NVIDIA_NIM_API_KEY` is configured anywhere in
  this repository or environment. The request construction, auth header,
  error-code mapping, response parsing, streaming SSE parsing and bounded
  input validation for those paths are covered by
  `tests/test_nvidia_nim.py` (9 tests, mocked HTTP, passing). Ruff and the
  full project test suite (46 tests) pass with this module added.
- Earlier in this session, a direct `curl`/`urllib` request to
  `https://build.nvidia.com` (the human-browsable catalog *website*, a
  different host) and to `1.1.1.1` failed from this sandbox's default
  network. That is unrelated to this adapter: `integrate.api.nvidia.com` (the
  actual API host this adapter calls) is reachable, as the live result above
  demonstrates.

## Setup (action required from you)

1. Create a free NVIDIA Build account and generate a key at
   https://build.nvidia.com -- do not assume it is free or unlimited; NVIDIA's
   current quota/pricing terms must be checked on that page at signup time,
   and some models additionally require your org to have "Public API
   Endpoints" access enabled (see gotcha above).
2. Put the key in a local, git-ignored file (e.g. `.secrets/nvidia-nim-key` or
   your shell environment) as `NVIDIA_NIM_API_KEY=nvapi-...`. Never commit it
   or paste it into chat, logs, or source.
3. From a machine with real network access to `integrate.api.nvidia.com`, run:
   ```sh
   export NVIDIA_NIM_API_KEY=nvapi-...
   curl -s http://127.0.0.1:8000/api/nvidia/status
   ```
   or call it directly: `GET https://integrate.api.nvidia.com/v1/models` with
   the `Authorization: Bearer` header, to get the first real connectivity
   result for this integration.

## Local NVIDIA model deployment (hardware reality)

This laptop has **no NVIDIA GPU** (Intel Iris Xe integrated graphics only; no
`nvidia-smi`, no CUDA) and **7.5 GiB of total RAM**, not 32 GiB -- see
[HARDWARE_ROADMAP.md](HARDWARE_ROADMAP.md) for the full, previously-verified
hardware report. Running an NVIDIA NIM container locally, or loading a
multi-billion-parameter NVIDIA model (e.g. the untested, uncommitted
`scripts/download-nvidia-reference.py`, which targets a 2.8 GB
Nemotron-3-Nano-4B GGUF for storage only), is not something this machine can
do for inference without heavy swapping, and that script has not been run --
downloading it requires your explicit approval first, consistent with this
project's "ask before large downloads" policy. Use hosted NIM inference
(above) for anything beyond what the existing pinned SmolLM2 135M Ollama
reference already covers locally.

## Not claimed

No model weights were downloaded by this change. No NVIDIA API has been
called from this environment. No capability is assumed beyond what NVIDIA's
own published documentation states. Rate limits, free-tier quotas and
per-model entitlements must be rechecked on https://build.nvidia.com at the
time you actually use this integration.
