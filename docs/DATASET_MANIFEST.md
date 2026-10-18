# Dataset manifest — Phase 5

Every dataset NEXORA has ever trained on, as actually recorded on disk this
session (`artifacts/datasets/*/manifest.json`), each integrity-checked by
`nexora.data_engine.load_dataset` on every load (sha256-pinned files,
`approved: true`, an allowed license, rejected otherwise).

| Dataset id | License | Documents | Pipeline | Source/provenance | Used by |
| --- | --- | --- | --- | --- | --- |
| `python-tutorial-bd831076dc61` | PSF-2.0 | 835 | text-v2.1 | Human-authored CPython 3.13.0 tutorial, PSF | `phase2-small-language` (selected), `phase2-tiny-language`, `phase2-small-low-lr` |
| `phase3-base-ddaa35f3eeb5` | PSF-2.0 | 750 | frozen-source-expansion-v1 | Phase 2 approved sources with Phase 3 holdouts reserved | `phase3-baseline-s42/s43`, `phase3-compact-s42/s43` |
| `phase3-expanded-61dc5275e032` | PSF-2.0 | 1,514 | frozen-source-expansion-v1 | Version-pinned CPython documentation, source-level fixed holdouts, 12-word contamination exclusion | `phase3-wider-s42/s43`, `phase3-compatible-fork` |
| `localai-docs-pilot-5bbfc531d2a3` | MIT | 58 | text-v2.1 | Pinned MIT LocalAI documentation, notices retained | `localai-docs-pilot-8` (separate, not promoted; test perplexity 897.45, reported not hidden) |
| **`instruction-pilot-v1`** (new this pass) | CC0-1.0 | 61 | instruction-pilot-v1 | NEXORA-engineering-authored original instruction/response examples, written specifically for Phase 5 -- no third-party content | `phase5-instruction-pilot-v1` (evaluated, **not promoted** -- see `docs/INSTRUCTION_TUNING.md`) |

## Required fields, and where each dataset satisfies them

Per manifest (all five satisfy all of these -- verified by reading each
`manifest.json` this session, not assumed):

- **Source**: recorded in `provenance` and, for the `text-v2.1`/
  `frozen-source-expansion-v1` pipelines, per-document `sources{}` with
  original URLs and raw sha256 hashes.
- **License**: one of `{MIT, Apache-2.0, CC0-1.0, public-domain, PSF-2.0}`
  (`nexora.data_engine.LICENSES`); anything else is refused at load time.
- **Dataset version**: a single sha256 `version` field per manifest.
- **Content hash**: every split file has a pinned sha256 in `files{}`;
  every document additionally carries its own sha256 `id` in the
  `text-v2.1`/pilot pipelines.
- **Token count**: recorded per run in each `tokens.json` (shard-level
  token counts), not per raw dataset -- token count depends on the
  tokenizer trained for that specific run.
- **Deduplication status**: `nexora.datasets.prepare()` and
  `scripts/prepare-instruction-pilot.py` both dedupe by exact-text sha256
  before splitting; `scripts/evaluate_matrix.py` additionally checks
  cross-split exact-document and 12-word-shingle overlap for the phase2/3
  matrix (all zero exact overlap, reported shingle overlap explicitly, not
  hidden).
- **Training approval**: `approved: true` plus a named `reviewer` field in
  every manifest; `catalogs/manifest.json` entries default to
  `training_approved: false` until individually reviewed (none have been
  promoted to training-approved).
- **Split assignment**: `train`/`validation`/`test`, assigned deterministically
  by sorted content hash (not random, not time-ordered) -- documented in
  each `prepare`/build function.

## Pretraining vs. instruction-tuning separation

`python-tutorial-*` and `phase3-*` are plain-text pretraining corpora
(continuous CPython documentation prose). `instruction-pilot-v1` is the
first dataset in this project formatted as discrete instruction/response
pairs. They are kept as **separate dataset ids, never merged** -- each
`create_run` call trains a fresh tokenizer and model from exactly one
dataset id, so there is no accidental blending. See
`docs/INSTRUCTION_TUNING.md` for why keeping them separate (rather than
mixing) was also the right experimental choice for measuring whether the
architecture can learn the instruction pattern at all.

## Not done this pass, and why

The Phase 5 prompt asks for separate datasets across ten categories
(general LM, instruction, programming, WordPress/WooCommerce, Shopify, tool
calling, task planning, document QA, agent error recovery, evaluation-only
benchmarks). Only general LM (pre-existing) and instruction (new this pass)
exist. Building the other eight with the same provenance/hash/dedup rigor
used above is real, multi-session work -- doing it shallowly just to check
a box would produce datasets no more trustworthy than inventing numbers,
which this project's own rules forbid. `docs/NEXORA_TRAINING_STRATEGY.md`
sets the priority order for what comes next, and expanding data diversity
is priority #2 there.
