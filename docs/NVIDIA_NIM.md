# NVIDIA NIM integration

Updated 2026-10-18. NEXORA uses `https://integrate.api.nvidia.com/v1`
with server-side Bearer authentication. Set `NVIDIA_NIM_API_KEY` in the API
process environment; `NVIDIA_API_KEY` is also accepted. The canonical project
variable takes precedence when both are nonempty. Restart the API after setting
its environment. Files containing secrets are not automatically loaded.
Never commit keys, paste them into chat, or put them in frontend configuration.

## Implemented routes

| NEXORA route | NVIDIA route | Bounds |
| --- | --- | --- |
| GET `/api/nvidia/models` | GET `/models` | Five-minute cache |
| GET `/api/nvidia/status` | GET `/models` | Current catalog connectivity and credential presence |
| POST `/api/nvidia/generate` | POST `/chat/completions` | 50 messages, 8,000 characters each, 4,096 output tokens |
| POST `/api/nvidia/stream` | POST `/chat/completions` | Same bounds; final text deltas only |
| POST `/api/nvidia/responses` | POST `/responses` | String input up to 32,000 characters; 4,096 output tokens; nonstreaming |
| POST `/api/nvidia/embeddings` | POST `/embeddings` | 32 inputs |

Chat accepts `temperature`, `top_p`, optional `tools` and `tool_choice`.
Responses accepts `input`, `model`, `temperature`, `top_p`, and
`max_output_tokens`. It returns final message text, status, usage, and incomplete
details. Reasoning items and `reasoning_content` are not returned or audited.
The Responses adapter supports text requests only: no tool execution, conversation
storage, response retrieval, background jobs, or streaming. It never silently
falls back to Chat Completions. An incomplete result remains labeled incomplete.

NVIDIA's [NIM reference](https://docs.nvidia.com/nim/large-language-models/1.12.0/api-reference.html#experimental-support-for-the-openai-responses-api)
labels Responses support experimental. This does not establish availability for
every hosted model/account. The [GPT-OSS-20B Chat reference](https://docs.api.nvidia.com/nim/reference/openai-gpt-oss-20b-infer)
documents the Chat Completions endpoint. Model-specific capabilities and current
account terms take precedence over general OpenAI compatibility.

## Run the supplied requests through NEXORA

With a key configured in the server's environment:

```sh
curl --fail-with-body http://127.0.0.1:8000/api/nvidia/generate \
  -H 'Content-Type: application/json' \
  -d '{"model":"openai/gpt-oss-20b","messages":[{"role":"user","content":"Which number is larger, 9.11 or 9.8?"}],"temperature":1,"top_p":1,"max_tokens":4096}'

curl --fail-with-body http://127.0.0.1:8000/api/nvidia/responses \
  -H 'Content-Type: application/json' \
  -d '{"model":"openai/gpt-oss-20b","input":"Which number is larger, 9.11 or 9.8?","temperature":1,"top_p":1,"max_output_tokens":4096}'
```

In the supplied Python SDK examples, replace the literal `api_key="$NVIDIA_API_KEY"`
with `api_key=os.environ["NVIDIA_API_KEY"]` and add `import os`. Python does not
expand shell variables inside strings. For Chat, print only
`completion.choices[0].message.content`; for Responses, print `response.output_text`
instead of dumping the full response. The SDK is optional; NEXORA's adapter uses
its existing HTTP client and requires no new dependency.

## Verification and limitations

Public model discovery previously worked live without a key. Unit tests exercise
payloads, credential precedence, output parsing, reasoning exclusion, incomplete
responses, error shapes and bounds. Hosted Chat/Responses generation has **not**
been verified live: no credential was supplied. A configured key does not prove
entitlement, credit availability, or successful generation; the legacy status
field `generation_available` means credential present only.

Missing credentials return 503 before a request. Upstream 401, 403, 404 and 429
are distinguished. A 403 indicates refusal; entitlement/access restrictions are
possible causes, not proof that a key authenticated successfully. Hosted calls
send your prompts to NVIDIA and may consume account quota. No unlimited free
service is claimed. No hosted output is automatically used as training data.

The separate Nemotron 4B GGUF has been downloaded with approval and SHA-256
verified for **storage only**; see `tooling/nvidia/nano4b-storage-manifest.json`.
It is not loaded by this adapter. GPT-OSS-20B is hosted, not installed locally;
this laptop has no NVIDIA GPU and approximately 7.5 GiB total RAM.
