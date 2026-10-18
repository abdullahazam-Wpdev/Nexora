# Integration registry

| Provider | Purpose | Permission | Authentication | Cost | Setup | Status |
| --- | --- | --- | --- | --- | --- | --- |
| NEXORA Core | Independent local inference | Read local model artifacts | Localhost ownership | No API charges | Train with `python -m nexora.train` | Working |
| Ollama / SmolLM2 135M | External open-weight reference inference | Fixed localhost endpoint and pinned model digest; no automatic training | Localhost ownership | Local CPU/storage | `scripts/install-ollama.sh`, `scripts/ollama.sh start`, `scripts/prepare-reference.sh` | Adapter tested; live runtime verification recorded in reference setup report |
| REA / Hopper demo | Local artifact/source research tooling | Explicit local targets; native demo license approved | Local user processes | No purchase | `scripts/rea.sh`; see reference setup report | Portable analysis verified; native provider status recorded separately |
| SQLite | Project, memory, audit and dataset metadata | Read/write configured artifact root | Local filesystem | Free | Automatic migration at API startup | Working |
| PostgreSQL | Future scalable persistence | Local database access | `.env` password | Free local software | Install rootless Podman in host shell, configure `.env`, start Compose; adapter still pending | Not connected |
| Redis | Future queue/cache | Local service access | Localhost binding; production auth pending | No hosted service | Optional Compose; queue integration still pending | Not connected |
| Search, GitHub, WordPress, Shopify, email/calendar | Future modules | Provider-specific minimum scopes to be documented before enabling | Future environment variables or secret store | Provider dependent, approval before charges | No setup performed | Not configured |
| Commercial model APIs | Optional future comparison only | No permissions granted | No keys configured | Could be paid; explicit approval required | Not required by Core | Disabled |
| NVIDIA NIM | Hosted catalog inference (chat, streaming, embeddings) + public model discovery | `NVIDIA_NIM_API_KEY` for generation only; model listing needs no key; never hardcoded | Bearer token via env var | Depends on NVIDIA's current terms; check before use | Adapter in `nexora/nvidia_nim.py`; routes `/api/nvidia/*` | Model discovery verified live (81 models, no key); generation implemented, needs your key (see [NVIDIA_NIM.md](NVIDIA_NIM.md)) |

Never place credentials in source, client JavaScript, committed files, audit details or training documents.
