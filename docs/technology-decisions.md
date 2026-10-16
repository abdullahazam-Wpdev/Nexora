# Technology decisions — 2026-10-16

Official documentation was reviewed before implementation. Exact installed Python versions are in `requirements.lock`; JavaScript versions and integrity hashes are in `frontend/package-lock.json`. The local Node binary was verified against the official distribution SHA-256 manifest in `.tools/node-shasums.txt`.

| Technology | Decision | License / source |
| --- | --- | --- |
| PyTorch CPU | Installed; explicit causal SDPA, autograd, AdamW; no pretrained model | BSD-3-Clause; https://docs.pytorch.org/docs/stable/generated/torch.nn.functional.scaled_dot_product_attention |
| Hugging Face Tokenizers | Installed; local byte-level BPE with complete byte alphabet | Apache-2.0; https://huggingface.co/docs/tokenizers/ |
| Safetensors | Installed; non-pickle inference weights | Apache-2.0; https://huggingface.co/docs/safetensors/index |
| FastAPI / Uvicorn | Installed; typed local API and OpenAPI | MIT / BSD-3-Clause; https://fastapi.tiangolo.com/ |
| Next.js / React / TypeScript | Installed; production-built responsive dashboard; Next updated to resolve initial audit findings | MIT / MIT / Apache-2.0; https://nextjs.org/docs |
| SQLite | Active durable project, memory and audit storage; lower overhead in 8 GiB environment | Public domain; https://sqlite.org/docs.html |
| PostgreSQL 18 | Optional Compose only, not running or connected | PostgreSQL License; https://www.postgresql.org/docs/current/ |
| Redis 7.4 | Optional Compose only; queue not yet implemented | RSALv2 / SSPLv1 choice, not permissive OSI licensing; review before redistribution; https://redis.io/docs/latest/ |
| Podman / Compose | Rootless local infrastructure configuration supplied; unavailable in this sandbox | Apache-2.0; https://docs.podman.io/en/latest/ |
| Hugging Face Datasets | Deferred: small owned arithmetic fixtures do not need Arrow/dataset downloads | Apache-2.0; https://huggingface.co/docs/datasets/index |
| MLflow | Deferred: atomic JSON experiment records provide lightweight initial tracking | Apache-2.0; https://mlflow.org/docs/latest/ |
| lm-evaluation-harness | Deferred: meaningless for numerical smoke-model language benchmarking | MIT; https://github.com/EleutherAI/lm-evaluation-harness |
| Playwright Python | Installed for real browser QA on localhost; Chromium downloaded to application cache | Apache-2.0; https://playwright.dev/python/docs/intro |
| CUDA | Not installed; no NVIDIA hardware detected | NVIDIA proprietary toolkit terms; https://docs.nvidia.com/cuda/cuda-installation-guide-linux/ |
| Ruff | Reviewed, deferred; pytest, TypeScript, npm audit and browser QA are initial checks | MIT; https://docs.astral.sh/ruff/ |

Versions were resolved from registries available in this environment, not assumed from model knowledge. Optional container image tags are major/minor pinned rather than immutable digest pinned; verify and lock digests before deployment. npm audit checks the available advisory database and is not a guarantee of security. Production authentication, metrics export and secret management remain roadmap work. No service credentials are configured.
