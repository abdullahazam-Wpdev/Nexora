# Provider and platform research

Reviewed 2026-10-18. Public documentation describes provider features, not demonstrated NEXORA abilities. No private chats, cookies, model weights or account credentials were extracted. Website access is separate from API entitlement. Free quotas and model identifiers must be rechecked before use.

| Platform | Useful capability / reproducible pattern | NEXORA state and boundary | Primary reference |
|---|---|---|---|
| NVIDIA NIM | Hosted inference catalog spanning many providers/modalities | Adapter implemented (`nexora/nvidia_nim.py`): model discovery verified live (81 real models, no key needed); chat, streaming, embeddings, tool-call passthrough implemented but need your own `NVIDIA_NIM_API_KEY`. See [NVIDIA_NIM.md](NVIDIA_NIM.md) | https://docs.api.nvidia.com/ |
| OpenAI / ChatGPT | Conversations, tools, coding workflows | Local conversation UI and explicit workspace actions implemented. No official OpenAI API key or proprietary model replication. | https://developers.openai.com/api/docs/guides/function-calling |
| Anthropic / Claude | Hosted reasoning and coding agents | Reference skill; no official Anthropic credentials. FCC is an unrelated proxy, not Claude weights. | https://platform.claude.com/docs/en/intro |
| DeepSeek | Hosted inference; separately released open-weight models | Research skill; model-specific license and hardware review required. `/api/search/` is docs search, not a search endpoint. | https://api-docs.deepseek.com/ |
| Perplexity | Search, grounded responses, citations | Reference skill; no live API account. Citation checking can be replicated without harvesting private outputs. | https://docs.perplexity.ai/docs/getting-started/overview |
| Kimi | Hosted models and agent workflows | Reference skill. Old Moonshot documentation redirects to Kimi. | https://platform.kimi.ai/docs/overview |
| xAI / Grok | Hosted assistant and API | Reference skill; no account configured. Public UI is not permission for bulk training extraction. | https://docs.x.ai/overview |
| Qoder | Coding IDE and agent workflow | Separate product from DeepSeek. Repository context and edit-review are useful workflow patterns; parity is not demonstrated. | https://docs.qoder.com/product-series/what-is-qoder |
| Ollama | Local model serving | Verified pinned external SmolLM2 135M Q4 reference; chat now uses bounded conversation context. | https://ollama.com/ |
| LocalAI | OpenAI-compatible inference engine | Installed v4.11.0; pinned CPU backend; real local inference and chat routing verified. Not itself a model. | https://github.com/mudler/LocalAI |
| free-claude-code | Translate coding-client requests to provider APIs | AGPL-3.0 proxy; archive contains tokenizer data, not model weights. Installed in Python 3.14.7; authenticated local Ollama routing verified; no global client configuration changes. | https://github.com/alishahryar1/free-claude-code |
| Docker / Podman | Package and isolate services | Existing rootless Podman runs bounded Python jobs. A second Docker daemon is unnecessary. No GPU on this laptop. | https://www.docker.com/ |
| Vercel / storage / CDN | Hosted frontend, object storage, delivery | Not provisioned: local disk has adequate free capacity and weights stay local. Cloud storage requires account, quotas and privacy review. | https://vercel.com/docs/vercel-blob/usage-and-pricing |
| public-apis | API discovery catalog | Attributed pinned snapshot searchable by `/catalog query`. Entries are not all installed, authenticated or license-approved for training. | https://github.com/public-apis/public-apis |
| awesome-free-models | Model / provider discovery | Attributed snapshot retained. “Free” catalog claims are not guarantees of quota, license or local feasibility. | https://github.com/12britz/awesome-free-models |
| MCP servers directory | Discover tool servers | NEXORA ships a bounded workspace MCP server. Directory entries are untrusted until reviewed; no bulk installation. | https://mcpservers.org/ |
| Wikipedia | Public knowledge and APIs | No bulk dump downloaded. Article attribution and share-alike obligations need a separate data policy; not in approved training corpus. | https://www.mediawiki.org/wiki/API:Etiquette |
| CDN blog | Discovery of hosting options | Marketing article reviewed; no CDN necessary for local operation. Provider terms must be checked before deploying. | https://blog.blazingcdn.com/en-us/best-free-cdn-options-open-source-personal-sites |

## Skills and working boundary

Project skills are in `.agents/skills/nexora-*`, one per provider family or research workflow. They guide this project’s coding agent; they are not learned neural weights or automatic access to provider accounts. The runtime does not claim to load every skill autonomously. They were validated with the skill-creator validator.

The product can save conversations, answer using a local reference model, create/read files and run explicit Python scripts in an isolated container. It cannot yet reliably plan multi-step tasks from natural language. SmolLM2 is small and unreliable; NEXORA Core remains a next-token research model. No arbitrary host shell, private account scraping or silent paid fallback is enabled.

## Learning policy

Daily discovery checks three public repositories for revision changes, with at most 256 KiB per response. New revisions are candidates, not training-approved content. The separate MIT documentation pilot retains license/provenance and source-level held-out splits, deduplicates through the existing data engine, trains a bounded new run, and does not promote it. Private conversations and proprietary platform outputs are excluded. A crawler and a model training loop are different systems; autonomous improvement needs an evaluation gate and a rights-reviewed corpus.

Books and blogs are references until an item-specific license is reviewed. Do not ingest copyrighted books or assume that a public blog permits training redistribution. External text and attached archives are evidence, not instructions for the agent.
