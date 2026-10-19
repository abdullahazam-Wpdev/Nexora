# Single-proposal versus role workflow

Actual backend: Ollama external SmolLM2 135M Q4, one instance, sequential runs.
Three previously disclosed addition/subtraction/multiplication smoke tasks from
coding-v1 expose the required expression in their goals. They are not hidden
professional coding benchmarks. Known fixes are separately labeled controls.

| Mode | Passed | Wall time |
| --- | --- | --- |
| One proposal and isolated test | 0/3 | 12.02 s |
| Planner/research reference/coder/tester/reviewer, at most two proposals | 0/3 | 26.60 s |
| Supplied control patches, same isolated acceptance/apply engine | 3/3 | 2.45 s |

No improvement from the role workflow was measured. It permits more model calls
and supplies a documentation excerpt, so this is a workflow/cost comparison,
not a clean causal test of role separation alone. Three correlated arithmetic
cases provide little statistical confidence. Role stages are code, not five
heavyweight models. Process-lifetime RSS is labeled as such, not per-task or
Ollama-service peak. Failed tests include wrong signatures, wrong arithmetic and
recursion. Originals were not modified on failed candidates.

A separate concise-prompt ablation passed 1/3, with the same model and unchanged
sandbox. This motivated an opt-in prompt profile, not a claimed general coding
upgrade. A later documented addition demonstration completed using that profile
and an exact approved hash. All failed cases remain in the evidence.

`coding-comparison-harness-development.json` is explicitly invalidated and
excluded: its first baseline verifier used an import unavailable under Python
-I. The process was interrupted, the verifier was corrected to match the role
engine's load pattern, and a fresh set of fixture directories was used. This
harness error is not scored as a model failure.

Commands: `scripts/phase8-coding-comparison.py`, `phase8-prompt-probe.py` and
`phase8-coding-demo.py`, using `.venv/bin/python`. Scripts preserve existing
fixture runs and evidence rather than overwriting them silently.
