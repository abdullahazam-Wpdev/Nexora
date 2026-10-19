# Phase 9 baseline verification — 2026-10-19

Verified clean `35b212b`, research/phase8-computer-use, then branched to
research/phase9-reliability. Baseline regression: **96 passed, 14.91 seconds**.
The actual host remains 7.4789 GiB RAM, 4 physical/8 logical CPU cores, Intel
integrated graphics, no CUDA. Available RAM was approximately 1.56 GiB, swap
already used 6.85 GiB, free disk approximately 183 GiB. Swap is not extra RAM.

Reproduced standard coding **0/3**, concise **1/3** using fresh disposable
repositories. The successful addition candidate passed real Podman assertions,
rejected a wrong approval hash and applied only with its exact verified hash.
The browser navigate/type/click/assert/screenshot workflow passed again; its PNG
SHA-256 matched the stored artifact. Retrieval reproduced **3/3**, SmolLM2 exact
instructions **0/4**, and its recall probe failed.

Reloaded the Phase 8 wider tool pilot and reproduced **6/16** correct tools and
**14/16** valid JSON schemas. Verified selected Core checkpoint integrity and
SHA-256 `0b10d349fe2a8517544cd31cee03140eba7aa730fd1087ae01f0b02b1b56ee84`.
It remains 984,192 parameters, original tokenizer/context/data and 409,600
training tokens. Neither new assistant weights nor scratch pilots replace it.

Phase 8's controlled functionality is working; reliable general coding and
instruction following were never demonstrated. Phase 9 adds fresh reproduction
records rather than overwriting Phase 8 files. Baseline browser/code evidence is
in `evidence/phase9/baseline-integration.json`, screenshot in baseline-browser.png,
model probes in baseline.json and baseline-quality.json. Frontend type/build,
lint and the expanded regression suite are reported in PHASE9_DELIVERY.md.
