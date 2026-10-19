# Phase 9 data provenance

No ChatGPT/Claude/Kimi/Grok transcripts or private owner conversations were
harvested. No new external training corpus was downloaded. The only new download
was the owner-approved inference-only Qwen model with its separate Apache license.

Training corpora are original deterministic project fixtures, authored with AI
assistance for this research, explicitly CC0-1.0; not claimed human-only or
real-world distribution. Existing approved PSF technical data/tokenizer remain
unchanged. The old empty-argument tool corpus is kept separate from the mixed
instruction/argument corpus. Each pilot stores its actual dataset JSON, revision,
source IDs, license, source category, split and file SHA-256 beside the checkpoint.

Mixed instruction categories include QA, code, structured JSON, tool calls/tool
results, error correction, clarifying questions, refusal and exact formatting.
V1 used underspecified tool requests; V2 adds explicit argument values. Both
versions and failures are retained. Validation paraphrases share training
meanings/answers; test uses separate values/request wording. Exact prompt hashes
are disjoint, but shared synthetic templates remain. This is **not** a robust
source-family-held-out natural-language corpus. It must not support claims of
broad generalization. Final coding acceptance/control data is not used for Core
training or provided to the external proposer.

Evaluation fixtures in benchmarks/phase9-*.json and evidence are original CC0
project artifacts. The HTML grading correction is versioned/documented, rather
than silently preserving an invalid success. Existing data-engine and expansion
license/provenance/hash/dedup/frozen-source evaluation checks remain available.
More diverse licensed human-authored data, stronger family-level splits, overlap
review and an untouched final evaluation are required before scaling training.
