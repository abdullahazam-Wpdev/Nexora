# Research roadmap — Phase 3 update

Verified and delivered:

- Independently reproduced the Phase 2 984,192-parameter model's loss/perplexity exactly before changes; original 19 tests and integration checks rerun.
- Small approved PSF corpus expansion, source provenance/hashes/notices, indexed exact/near deduplication, 12-word contamination exclusion and immutable held-out suite/tokenizer.
- Measured CPU training/inference/resource/checkpoint costs; reduced monitor/evaluation overhead with tested likelihood equivalence.
- Configurable bounded architecture framework with hardware feasibility probes and matched-token two-seed comparison across 172K/984K/2.12M models.
- Matrix safety cutoff exercised; all six common step-128 checkpoints compared fairly. Dataset-size ablation remains unexecuted. Persistent retry-safe deadline added and tested after the controller retry limitation was identified.
- Generation/prefix-overlap/repetition and strict instruction probes; no demonstrated instruction-following capability.
- Actual interrupted-worker and SIGKILL recovery, integrity checks, cancellation and API-restart persistence; explicit tested v2/v3 checkpoint forks preserve parents.
- CPU scaling extrapolations and source-backed GPU workstation decision report. No GPU purchased or provisioned.

Next model milestone:

Local reference tooling update (2026-10-18): REA repository review and CLI,
Hopper demo setup, and a separately labeled Ollama/SmolLM2 inference adapter.
See [installation and verification](reverse-engineering-reference-setup.md).
The installed tiny reference failed constrained arithmetic/exact-output smoke
probes. Reference inference does not imply distillation or improve Core weights
by itself. Before a teacher experiment, compare fixed tasks, review output-training
terms, label synthetic provenance and obtain a fresh bounded training plan.

1. Use the ~1M model as baseline and run a truly matched-token data-size/domain-diversity ablation under a fresh explicitly bounded plan; do not widen merely to increase parameter count.
2. Expand human-authored licensed language diversity only with rights/quality/size review and an untouched new final test suite. Current few-hundred-kilobyte technical corpus is not sufficient for a capable assistant.
3. Repeat more seeds on AC power and base budgets on sustained training rates, with persistent transaction deadlines and interruption evidence.
4. Add human-reviewed instruction data, executable task tests and meaningful generalization evaluation before claiming assistant/coding/reasoning ability.
5. Validate a representative GPU benchmark and complete-system cost quote before purchasing hardware or approving any multi-hour job. GPU precision/RNG/scaler/DDP support remains future implementation work.

Still outside the delivered scope: reliable assistant/agents, arbitrary code/browser execution, specialist business/creative/authorized-security products, workforce/virtual office, multimodal models, multi-user authentication and public production deployment. PostgreSQL/Redis remain verified local services; SQLite still backs current project records. No dashboard redesign was undertaken.

## Local cowork integration — 2026-10-18

Delivered persistent local chat, explicit isolated file actions, rootless networkless Python execution with cancellation, a four-tool workspace MCP server, provider-specific project skills, attributed API/model catalogs, daily bounded revision discovery, and a separate eight-step MIT documentation training pilot. Ollama, LocalAI CPU inference and the isolated FCC-to-Ollama proxy passed real local chat checks. External hosted providers remain documentation references without configured accounts. No proprietary model weights were replicated.

The pilot's test perplexity is 897.45 on its own documentation split; it is not comparable to the earlier Core evaluation's different corpus/tokenizer. It is not promoted. Next: larger reviewed data, stable evaluations, stronger instruction-following reference feasibility, then bounded agent planning/edit-review evaluations. Current workspace tools are user-directed, not a validated autonomous coding agent. See `cowork-delivery.md` for exact evidence and limitations.


## Phase 7 — bounded coding workflow, 2026-10-18

Delivered durable task execution, registered-source inspection, staged Python fixes, real sandbox acceptance, bounded revision, deterministic Planner/Researcher/Coder/Tester/Reviewer stages, explicit hash-bound apply, typed project memory, skills, source-backed chat research, calculation/literal-citation verification and the screenshot-based functional light workspace. Two OpenAI-through-NVIDIA modalities are represented honestly: GPT-OSS chat requires a key/consent, Whisper speech requires its separate service. Approved NVIDIA 4B weights are storage-only.

SmolLM2 utility repairs: 0/20 before and after prompt clarification; supplied controls 20/20. Core masked tool training: 16/16 valid JSON, only 2/16 correct tools; selected model unchanged. Full scope and failures: `PHASE7_DELIVERY.md`, `PHASE7_EVALUATION.md`. Next: stronger backend evaluation and richer balanced tool/argument tasks before broader autonomy or foundation scaling.
