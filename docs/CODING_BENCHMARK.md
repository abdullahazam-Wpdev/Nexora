# Coding benchmark protocol

`benchmarks/phase9-coding.json` contains 20 original CC0 requests/starting files;
`phase9-acceptance.json` contains acceptance/control fixtures withheld from model
prompts. Requests were frozen before new backend evaluation. Tasks cover Python,
JavaScript, TypeScript, Web Request/Response route units, HTML/CSS, API utilities,
test repair, two multi-file changes and blocked FastAPI/PHP/WordPress cases.

Every attempt uses a clean disposable folder, precise request, source-only
context, scoped file list, deterministic assertion where feasible, retained
originals and exact-hash apply approval. Final mixed-suite runs allow one proposal;
interactive tasks allow at most two. Global evaluation controller stops after
180 seconds. Podman has network none, read-only root/workspace, no capabilities,
UID 65534, 32 PIDs, 0.5 CPU, no swap and a 10-second/output budget. Python uses
96 MiB; Node/TypeScript 256 MiB. Existing pinned Python image is reused with
read-only copies of the already installed Node loader/libraries and TS compiler.
No extra image/system package was installed.

TypeScript grading is transpilation plus runtime behavior, not a complete semantic
type-check/build suite. Web route grading uses Node's real Response API, not a
running Next server. HTML/CSS grading is structural/static, not visual rendering.
FastAPI and two PHP/WordPress cases are **blocked**, not passed via mocks/AST checks.

| Measurement | Model passes | Controls | Runtime blocked |
| --- | --- | --- | --- |
| Original three exposed arithmetic cases, Qwen | 3/3 | Previously verified | 0 |
| Mixed suite, approved 1,152 MiB JSON-profile study | 2/17 | 17/17 | 3 |
| Mixed suite, one-file plain-source 900 MiB regression | 1/17 | 17/17 | 3 |

Initial raw/structured 900 MiB runs include provider failures and are diagnostic
records, not complete capability measurements. HTTP 503/resource failures are
not model reasoning failures. The 1,152 MiB study finished all supported requests.

The original HTML assertion was vacuously true for a document without any labels.
A corrected assertion requires a matching label and input; stored candidates
were rescored by real execution without regenerating model outputs. The apparent
3/17 score therefore became **2/17**. Controls still pass. Raw initial grade,
correction and rescore evidence are retained. This and repeated protocol changes
mean the suite is useful regression evidence, not an unbiased final accuracy
claim. Freeze a fresh task-family holdout before future model/prompt selection.

Pure Python rootless execution and new Node/TS profiles are real; arbitrary
framework builds or unrestricted host execution are not supported. Run
`scripts/prepare-node-sandbox.py` on a clean installation, then explicit evaluation
scripts with a fresh label; never silently overwrite previous fixture directories.
