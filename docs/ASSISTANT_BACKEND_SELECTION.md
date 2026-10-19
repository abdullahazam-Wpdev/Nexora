# Assistant backend selection

Selected operational backend remains external Apache-2.0
`smollm2:135m-instruct-q4_K_M`,134.52M parameters,105,466,867-byte Ollama package,
digest fd316850965252d917ac2bf811adef10ba91e129e5f2809f2a24a8501ff73e4f.
Its measured normal-cap stability is useful; professional coding ability is absent
(0/31 passed,8 blocked in this suite). Context768,Q4_K_M,two CPU threads.
Median 84.64tokens/s and0.771s first delta are this run's metrics, not guarantees.

Qwen2.5-Coder0.5B Apache-2.0 Q4_K_M is already downloaded and disabled. Its prior
2/17 coding result used temporary1152MiB; no permission for another enlarged run is
inferred. Nemotron4B remains storage-only. No new download, dependency or paid call.
Gemma/other candidates were not downloaded or evaluated; insufficient current
headroom and no substantial-download approval. No stronger sustainable candidate
has been demonstrated. This is a documented unmet target, not a substitute success.

NVIDIA NIM catalog was reachable,81 models, but status reported key_configured=false
and generation_available=false. Existing hosted adapter requires both configured
credentials and allow_hosted per request; never automatic fallback. Hosted inference
is explicitly external. Core remains independent research text prediction; LocalAI
stays stopped; FCC uses Smol weights, not Claude. UI/API identify these separately.

Official references reviewed 2026-10-19:
https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct
https://ollama.com/blog/new-model-scheduling
https://github.com/ollama/ollama/blob/main/docs/faq.mdx
License/model identity also retained in tooling/reference manifests.
