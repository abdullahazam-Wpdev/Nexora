# Phase 8 model and system diagnostics

| Test | Selected independent Core | External Ollama SmolLM2 135M Q4 | Hosted NVIDIA |
| --- | --- | --- | --- |
| Four disclosed exact-output instructions | 0/4 | 0/4 | Not run: no key |
| One two-turn code-word recall | Not measured | Failed | Not run |
| Three arithmetic coding smoke tasks, standard roles | Not rerun; prior tool/coding failure records preserved | 0/3 | Not run |
| Same coding smoke set, short-prompt ablation | Not applicable | 1/3 | Not run |
| Recorded documentation-to-approved-addition demo | Not the backend | Passed with concise prompt | Not run |
| New supervised synthetic tool matrix | Separate pilots, 1/16–6/16 correct tools | Not evaluated on that matrix | Not run |

System checks are separate from model intelligence: three source-index retrieval
queries passed top-1/exact citation checks and namespace isolation; real browser
form verification passed; supplied Python controls passed 3/3. Permission,
recovery and schema cases are automated tests, not model reasoning successes.

Quality-evaluation.json records raw reference replies and protocol. Recall uses
one supplied assistant acknowledgement in history, not an independently generated
first-turn answer. Neither model demonstrated reliable instruction following or
professional coding. Four prompts, three arithmetic functions and one recall
case are narrow diagnostics. Multi-step browser success follows an approved
fixed plan, not a learned autonomous planner. No universal benchmark score is
claimed. The prior harder coding-v2 0/20 remains relevant and is not erased by
the successful simple addition example.

The matrix in NEXORA_CORE_SCALING.md evaluates JSON schema and tool identity;
it does not evaluate meaningful arguments or genuine multi-step reasoning.
Unexecuted benchmarks include broad multilingual coding, real JS/TS/PHP builds,
semantic citation entailment, long-horizon computer use and account-backed speech.

Run: `.venv/bin/python scripts/phase8-quality-eval.py` and the explicit coding
scripts. Network dependencies and model identity are recorded. Fixtures are
public/authored; private conversations never enter training or benchmark files.
