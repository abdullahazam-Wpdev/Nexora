# Dataset strategy and delivered pipeline

The first human-authored language corpus is a **263,879-byte** version-pinned selection of CPython v3.13.0 tutorial sources and its license stack. Acquisition is bounded to 700,000 total bytes and a per-file cap; every raw file now has a pinned SHA-256 in `configs/python-tutorial.sources.json`. No pretrained weights, proprietary model outputs or authenticated scraping are used.

The [PSF documentation license](https://docs.python.org/3/license.html) permits reuse subject to notices and other conditions. The reviewed source catalog records PSF-2.0, provenance, reviewer, maximum size and license evidence. Full upstream copyright/license text is retained with every prepared dataset's notices; extraction/filtering changes are recorded in acquisition.json. This is an engineering license review, not automatic verification of arbitrary ownership or permission. Unreviewed sources are rejected until explicitly approved. No third-party corpus is redistributed in Git.

## Working flow

1. Source catalog is reviewed before `--approve-download` permits acquisition. Downloader is CLI-only and restricted to version-pinned CPython raw URLs; redirects and size/hash mismatches fail closed. It never follows authenticated sessions.
2. Strict UTF-8 decoding; NFC normalization; conservative RST markup extraction. Paragraph chunks have no overlapping window and retain source URL/hash. Long chunks are split without overlap.
3. Secret/email/key/payment-number patterns reject suspicious paragraphs. Length, alphabetic ratio and control-character checks reject low-quality text. These conservative rules can reject benign examples and cannot guarantee privacy.
4. Canonical whitespace/case normalization for exact deduplication; 12-word shingle Jaccard >0.85 removes near duplicates. Hashes and per-reason rejection counts are retained.
5. Whole source files are assigned deterministically to train/validation/test **before** tokenization. Duplicate held-out passages are dropped, not moved into training. This corpus holds out `stdlib` for validation and `controlflow` for final test. Domain concepts can still overlap.
6. BPE is trained only on train text, with complete byte alphabet plus UNK/EOS. Every split is packed separately with document EOS boundaries and mapped uint16 NumPy shards. No random sampler crosses a split.
7. Content-derived dataset version, source hashes, pipeline version, quality report, tokenizer hash and token-shard hashes are linked to each run. Resume checks all of them.

Working APIs: POST/GET `/api/research/datasets`; POST `/api/research/runs` selects a real dataset ID. Original `/api/datasets` ingestion remains compatible; research training uses the versioned research dataset catalog. Source-level grouping is supplied explicitly by the data reviewer, so falsely assigning related passages to different sources can defeat holdout semantics.

Actual quality results: 1,298 input chunks; 835 accepted (642 train, 48 validation, 145 test); 437 quality rejections and 26 sensitive-pattern rejections. No exact/near duplicate was found in this selection under the configured criteria. Eleven training source files, one validation file, one test file. See evidence/phase2/dataset-quality.json.

## Future sources and domains

| Category | Next source/review requirement | Evaluation prerequisite |
| --- | --- | --- |
| General language | Independently licensed prose, author/source provenance and jurisdiction review | Multiple independent held-out sources |
| Technical documentation | Small version-pinned permissive official docs, retained notices | Unseen projects/chapters |
| Mathematics/reasoning | Owned procedural problems plus reviewed human explanations | New templates and numeric ranges |
| Programming/web development | Permissively licensed code with repository-level splits | Executed unit tests and withheld repositories |
| WordPress/Shopify | Platform documentation only after per-source terms review | Local sandbox tasks; no private merchant data |
| Defensive cybersecurity | Authorized labs and openly licensed defensive material | Scope-limited remediation/verification tasks |
| Research | Licensed papers/datasets with per-item rights | Held-out sources and reproducible citations |
| Multilingual | Verified human-authored multilingual corpora | Language identification beyond script heuristics |
| Instruction following | Explicit training rights, human/allowed synthetic provenance | Independent behavior and safety evaluation |

Do not expect this sub-million-token corpus or current small models to learn all domains. Avoid indiscriminate scraping, unresolved copyright assertions, secrets and proprietary-model training outputs. The included source-discovery catalog is deliberately curated rather than an internet crawler.
