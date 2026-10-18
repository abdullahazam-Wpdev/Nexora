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
