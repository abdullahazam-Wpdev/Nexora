"""Render delivery tables from measured evidence, without manufacturing unavailable metrics."""

import json, statistics
from pathlib import Path

root = Path(__file__).resolve().parent.parent
docs = root / "docs"
e = docs / "evidence/phase10"
load = lambda name: json.loads((e / name).read_text())
code = load("coding-rescore.json")
raw = load("coding-final.json")
core = load("core-comparison.json")
mem = load("inference-memory.json")
selected = load("selected-core.json")
research = load("research-live.json")
quality = load("answer-quality.json")
samples = [r["inference"] for r in raw["records"] if r.get("inference")]
tps = statistics.median(r["tokens_per_second"] for r in samples)
ttft = statistics.median(r["ttft_seconds"] for r in samples)


def put(name, text):
    (docs / name).write_text(text.strip() + "\n")


put(
    "CODING_BENCHMARK_V2.md",
    f"""# Frozen coding benchmark v2

31 original fixture tasks, frozen before the Phase10 proposer work and final inference.
`benchmarks/phase10/tasks.json`, `acceptance.json`, `freeze.json` retain exact hashes,
requests, existing-file scope, budgets and pass rules. Acceptance and supplied control
patches are not included in model prompts. Development uses the already-consumed
Phase9 suite. A final run has one proposal per task and refuses overwriting evidence.
Freeze author-code hash refers to the pre-format authoring source; subsequent formatting
is not represented as an unchanged byte hash. Acceptance files remain hash-identical.

Python transforms, API helpers, permissions, multi-file imports, JS, strict TS diagnostics,
HTML/CSS, JSON, Markdown and commerce-unit fixtures are included. FastAPI, PHP,
WordPress PHP, React/Next rendering and YAML execution remain explicitly blocked.
Web Response and commerce utilities are unit profiles, not framework deployments.

Raw run: {raw["summary"]}. Python controls subsequently exposed missing /workspace
on sys.path under Python -I. Fixed inside the container, preserving isolation. Stored
proposals were rescored without any new inference. Three strict TS control programs
failed within the existing 10s/256MiB profile and become harness blocks, not model failures.
Corrected: **{code["summary"]["passed"]} passed, {code["summary"]["failed"]} failed,
{code["summary"]["blocked"]} blocked / 31 total**. Supplied controls: 23 passed.
Do not remove blocked cases from the headline denominator or call this a pristine
validated professional benchmark. Final fixtures are now consumed; no further tuning
or backend selection used their outputs. Next model selection requires a fresh suite.

Raw task IDs, attempt events, timings, invalid-patch/timeout categories and inference
metrics remain in `evidence/phase10/coding-final.json`; corrected assertions/control
outputs remain in coding-rescore.json. Agent RSS field is a snapshot, not a measured
peak. Tool counts count sandbox invocations, not inferred reasoning steps. Final scorer
source and runtime revisions are committed; frozen acceptance code has SHA-256 hashes.

Reproduce in a fresh checkout/storage directory, never overwrite old evidence:
`.venv/bin/python scripts/phase10-evaluate.py`, then `scripts/phase10-controls.py`.
The harness correction changes supported module imports, not model prompts or targets.
""",
)
put(
    "MODEL_MEMORY_ANALYSIS.md",
    f"""# Model memory analysis

Measured physical RAM: 8,030,429,184 bytes (7.4789 GiB), four physical/eight logical CPUs,
no dedicated NVIDIA GPU. Initial available RAM 1,162,104,832 bytes; swap almost fully
used. RAM is not 32 GB. Do not infer memory headroom from installed swap.

Phase9's approved 1152MiB Qwen run **completed**. Three 900MiB runs OOMed. Its
397,821,516-byte Q4_K_M weights do not equal runtime RAM. Verified model metadata:
24 layers, dimension896,14 attention heads,2 KV heads, head dimension64. An f16 KV
estimate at512 tokens is 2*24*512*2*64*2 = 6,291,456 bytes; at1024 it is12,582,912.
KV alone does not explain the cap hit. Earlier observed compute buffers approximately
298.5MiB, model mappings/cache, allocator/backend and service overhead also contribute.
We cannot isolate fragmentation as a cause or prove all prior background concurrency
absent. The direct failure evidence is service cgroup OOM under900MiB. Increasing the
cap did not establish sustained operation under the normal limit. No repeat OOM trial.

Current Smol run: sampled host Ollama/runner RSS sum peak
**{mem["peak_sampled_process_tree_rss_bytes"]:,} bytes**; service cgroup lifetime peak
492,204,032 bytes (including cache and earlier requests). Service MemoryMax943,718,400,
MemorySwapMax0, CPU quota200%, one model, keepalive0, two inference threads,context768,
num_batch16. Host ps sampling fixes the prior Flatpak-zero-RSS reporting mistake.
Sampling began after evaluation start; RSS sum may double-count shared pages. This
is neither PSS nor isolated model allocation. Full samples/swap/available RAM in
inference-memory.json. Background swap changes do not prove model swap use (service
swap is disabled). Median decode {tps:.2f} tokens/s, first delta {ttft:.3f}s,26 calls.

`compute_budget.py` uses a nonblocking flock shared across processes and500MiB
available-memory admission floor. Research/legacy/tool/instruction training and
managed Core/reference/sidecar/shared assistant calls participate. Legacy coding now
uses the same pinned reference adapter. Direct external Ollama/FCC clients are outside
this application's admission gate; do not run them alongside training. Running a
training job causes new managed inference to return429; low memory returns503.
These are admission/step checks, not a total-system RAM guarantee or thermal daemon.
""",
)
put(
    "ASSISTANT_BACKEND_SELECTION.md",
    f"""# Assistant backend selection

Selected operational backend remains external Apache-2.0
`smollm2:135m-instruct-q4_K_M`,134.52M parameters,105,466,867-byte Ollama package,
digest fd316850965252d917ac2bf811adef10ba91e129e5f2809f2a24a8501ff73e4f.
Its measured normal-cap stability is useful; professional coding ability is absent
(0/31 passed,8 blocked in this suite). Context768,Q4_K_M,two CPU threads.
Median {tps:.2f}tokens/s and{ttft:.3f}s first delta are this run's metrics, not guarantees.

Qwen2.5-Coder0.5B Apache-2.0 Q4_K_M is already downloaded and disabled. Its prior
2/17 coding result used temporary1152MiB; no permission for another enlarged run is
inferred. Nemotron4B remains storage-only. No new download, dependency or paid call.
Gemma/other candidates were not downloaded or evaluated; insufficient current
headroom and no substantial-download approval. No stronger sustainable candidate
has been demonstrated. This is a documented unmet target, not a substitute success.

NVIDIA NIM catalog was reachable,81 models, but status reported key_configured=false
and generation_available=false. Existing hosted adapter requires both configured
credentials and allow_hosted per request; never automatic fallback. Hosted inference
is explicitly external. Core remains independent research text prediction; LocalAI
stays stopped; FCC uses Smol weights, not Claude. UI/API identify these separately.

Official references reviewed 2026-10-19:
https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct
https://ollama.com/blog/new-model-scheduling
https://github.com/ollama/ollama/blob/main/docs/faq.mdx
License/model identity also retained in tooling/reference manifests.
""",
)
put(
    "CODING_AGENT_RELIABILITY.md",
    """# Coding-agent reliability

Scoped existing files now include JSON/YAML/Markdown in addition to Python/JS/TS/PHP
source reads. Execution still requires a reviewed profile; accepting a YAML/PHP path
does not supply its parser/interpreter. No arbitrary host execution or package install.

Optional `patch_format: edits` accepts only1..8 exact replacements: path,old,new.
Every nonempty anchor must occur exactly once in the approved current source; unknown
paths, no-ops and ambiguous anchors fail. UI offers this experimental format explicitly;
default complete-file protocol remains unchanged for the frozen final run. Syntax/profile
checks, bounded feedback/retry and hidden acceptance remain required. JSON is parsed;
Python local imports permit only explicitly scoped top-level module names plus existing
stdlib allowlist, with execution remaining networkless/read-only/rootless.

After exact-hash approval and original-hash checks, journaled multi-file apply now
copies the actual applied scoped files into isolated staging and reruns owner acceptance.
Failure rolls touched files back and records interrupted status. This preserves owner
concurrent edits; a multi-file apply is journaled, not a filesystem-atomic transaction.
Tests cover minimal edits, stale sources, cancellation, partial recovery, concurrent edits,
real sandbox timeout/module imports, post-apply failure rollback and permission rejection.

Real two-file API demonstration is a supplied control, not model-generated intelligence.
Final model task success did not improve: 0 passes on31 fixtures,8 blocked. Keep approvals.
The shared proposer and safe patch machinery cannot manufacture model capability.
""",
)
put(
    "RESEARCH_VERIFICATION.md",
    f"""# Research and answer verification

Real run: keyless GitHub repository search for `fastapi in:name language:Python`,
rank/deduplicate URLs, read top3 in fresh isolated Chromium, extract text, hash evidence,
produce extractive cited answer, validate literal support. Status {research["status"]};
three sources read, {research["verification"]["supported"]}/3 extracts supported,
zero failed reads; runtime{research["seconds"]:.2f}s. Public evidence records URLs/hashes;
full excerpts remain private under artifacts/research-evidence/{research.get("evidence_id")}.json.
This is successful research plumbing, not proof of a semantically correct synthesized answer.

Canonical dedup removes fragment/tracking parameters; ranking uses query-term overlap.
Publication metadata is labeled unverified or unknown. Page URL after redirect is retained.
Browser validates public navigation, blocks active scripts/subresources, uses no personal
profile and treats page text as untrusted. No content may approve tools or change policy.
Source conflicts require review; automatic semantic fact-conflict resolution is not implemented.

`/api/answers/verify` rejects missing citation IDs, changed evidence hashes and claims
not present in cited text. A caller can supply forged evidence; this endpoint is not a
source-authentication mechanism. Supported text may itself be false or an instruction;
matching does not authorize execution. No arbitrary prose entailment claim.
Deterministic evaluation: {quality["correct"]}/{quality["total"]}, unsupported accepts
{quality["unsupported_accepted"]}, supported rejections{quality["supported_rejected"]}.
This is a literal gate's fixture rate, **not a model hallucination rate or citation truth rate**.
No proprietary services or private chats were scraped for training.
""",
)
lines = [
    "# NEXORA Core Phase10 bounded training",
    "",
    "Two random-initialized80-step pilots,2 CPU threads,96dim/2layers/4heads/context192,",
    "completion-only loss,AdamW0.002,seed42. Original selected checkpoint unchanged.",
    "",
    "| Run | Parameters | Validation loss | Held-out perplexity | Schema/tool identity | Exact args | Instruction exact | Train s | Peak RSS MiB |",
    "|---|---:|---:|---:|---|---|---|---:|---:|",
]
for r in core["experiments"]:
    lines.append(
        f"| {r['id']} | {r['parameters']} | {r['validation']['loss']:.6f} | {r['test']['perplexity']:.6f} | {r['tool_correct']}/{r['tool_total']} | {r['semantic_tool_exact']}/{r['tool_total']} | {r['instruction_exact']}/{r['instruction_total']} | {r['train_seconds']:.3f} | {r['resources']['peak_rss_mb']:.2f} |"
    )
lines += [
    "",
    "Narrow training uses8 deduplicated examples; diverse uses96. Validation24/test32 have",
    "disjoint parameter ranges and exact prompts; both trials share identical test requests.",
    "Both use the same generated families, so semantic/template overlap remains. Independent",
    "train-only tokenizers produce different vocabularies/parameter totals, so cross-run loss",
    "is not directly comparable. Eight tool cases cover only calculator/read_file, not11tools.",
    "Four exact instruction responses are repeated permission refusals; inspect per-case evidence.",
    "All8 tool argument sets are wrong. No professional reasoning or broad instruction claim.",
    "",
    "Original deterministic project fixtures,CC0-1.0,owner-authorized Phase10 research,source",
    "IDs/licenses/revisions/approval/splits in each private dataset manifest. Exact dedup and",
    "cross-split prompt checks run before training. No service outputs or external weights.",
    "Maximum80steps/45s/650MiB process guard and500MiB available floor; no promotion.",
    "Dataset/tokenizer/safetensors/result paths: artifacts/instruction-pilots/phase10-narrow-80/",
    "and phase10-diverse-80/. Loaded saved tensors exactly match originals.",
    "",
    f"Selected984192parameter checkpoint independently reloaded: validation loss{selected['evaluations']['validation']['loss']:.12f}, test loss{selected['evaluations']['test']['loss']:.12f}, test perplexity{selected['evaluations']['test']['perplexity']:.12f}. Full3777/12809 targets; exp(loss) verified.",
    "Selected language perplexity and synthetic instruction perplexity are different tasks.",
    "Changing training code invalidates the existing exact-code resume gate; retain old commit",
    "for prior-run resumption or fork a new run. Checkpoint inference compatibility is retained.",
]
put("NEXORA_CORE_2_TRAINING.md", "\n".join(lines))
put(
    "PHASE10_LIMITATIONS.md",
    """# Phase10 limitations

Professional coding and a stronger sustainable assistant remain unmet:0/31 model passes,
8 blocked cases, Smol reference weak, Qwen disabled, hosted generation credential-blocked.
No new large-model download or service-limit increase was attempted.

Strict TypeScript control execution exceeded the unchanged sandbox profile. FastAPI,
PHP/WordPress,React/Next renderer,YAML runtime remain blocked. Commerce fixtures are
small pure helpers, not deployments or account integrations. The final harness required
a Python import-path correction; preserved proposals were rescored, no model rerun.
No clean broader model-selection generalization claim. Fresh final suite needed next phase.

Literal citation support does not prove source truth, semantic entailment, currentness
or absence of conflicting facts. Caller-supplied evidence can be forged. No model
hallucination rate established. Research context was not integrated into a stronger coding
proposer in this phase. Existing optional public documentation path remains available.

Training uses tiny synthetic shared template families and only two tool types. Exact
argument scores0/8, instruction4/24 both trials; no promotion. Different vocabularies make
raw loss comparison confounded. One seed/no statistical significance. No continual training.

Admission locks protect participating project entry points, not external processes/direct
sidecar callers, total system RAM or a running job from sudden host pressure. Physical RAM
7.48GiB, swap nearly full; browser/build/testing can still contend. No system-wide installs,
cloud provision, private-data upload, unsupported desktop automation or spending.

No dedicated npm lint script exists. Typechecking/build and Ruff F are reported separately.
Single-owner localhost service remains a development deployment, not public multi-user security.
""",
)
print("Rendered evidence-based docs")
