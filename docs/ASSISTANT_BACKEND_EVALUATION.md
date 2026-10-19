# Assistant backend evaluation

One candidate was downloaded with explicit owner approval, not several models:
**Qwen2.5-Coder 0.5B Instruct, GGUF Q4_K_M**, 494.03M parameters, 24 layers,
14 attention/2 KV heads, original 32,768 context. Download total 397,821,516 bytes.
License is Apache-2.0, verified against the official
[model card](https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B-Instruct) and
[Ollama artifact](https://ollama.com/library/qwen2.5-coder:0.5b).
Pinned digest: `4ff64a7f502a08b7616edb8ca0a79eb1853fc363d842b7df4b46915d11a3fb09`.
`tooling/reference/qwen-coder.json` records model details and disable reason.
Ollama reports tools capability, but that does not establish reliable tool use.

Qwen passed **3/3 original arithmetic coding regressions** versus SmolLM2's
best **1/3**. Those tasks disclose the expression and are not professional tests.
The owner-approved 1,152 MiB rerun generated all 17 supported mixed-language
candidates, but only **2/17** passed corrected acceptance tests; three other
cases lacked a verified runtime. JSON wire constraints improved malformed file
maps, but the model frequently copied buggy code or emitted incomplete bodies.

Across that rerun, median first-token delay was **2.113 seconds** and median
model-reported decode rate **36.46 tokens/second**. The first short probe measured
1.663 seconds and 39.35 tokens/second. Cgroup MemoryPeak was **1,207,963,648 bytes**
(approximately 1,152 MiB), including file cache and service/runner accounting;
this is not isolated model RSS. Flatpak hid host process IDs, so the script's
zero RSS sample means **unavailable**, not zero RAM. Swap use increased by about
282 MiB across the rerun; background applications prevent causal attribution.

Extended 900 MiB runs hit cgroup OOM three times, including a short-context tool
session. Reducing prefill batch size/output/context did not establish sustained
900 MiB reliability. The cap protected the host and was never silently raised.
The owner separately approved one bounded 1,152 MiB study. Afterwards normal
900 MiB service was restored, the temporary profile removed, and Qwen disabled
by default. No continuing enlarged memory budget is assumed.

**Selected operating baseline: existing pinned SmolLM2 135M**, because it remains
within the established service profile. It is weak, not a professional assistant.
Qwen is a stored/evaluated candidate, not the production default or NEXORA Core.
Its new adapter, digest checks and attribution remain available for a future
reviewed resource profile. The UI shows it disabled; there is no paid fallback.
NVIDIA/other hosted credentials remain absent and were not required for offline
regressions. No hosted capability was counted as passing.
