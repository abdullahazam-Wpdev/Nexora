"""Phase 5 agent evaluation suite: real, automated, bounded test cases run
against actual backends (NEXORA Core, Ollama/SmolLM2). No invented scores;
a category with no implemented cases is reported as not_implemented, not
skipped silently.

This intentionally does NOT attempt every category in the Phase 5 prompt.
See docs/AGENT_EVALUATION.md for which categories have real cases here and
which are deferred, and why.
"""

import json
import re
import time

from nexora import reference
from nexora.config import ROOT, STORE
from nexora.research import infer_run

CORE_RUN_ID = "phase2-small-language"


def call_core(prompt, max_tokens=32):
    try:
        out = infer_run(CORE_RUN_ID, prompt, max_tokens, STORE)
        return out["text"].removeprefix(prompt)
    except Exception as exc:  # noqa: BLE001 -- eval harness must not crash on a bad backend
        return f"__ERROR__:{exc}"


def call_ollama(prompt, max_tokens=48):
    try:
        result = reference.request(
            "/api/generate",
            {
                "model": reference.MODEL,
                "prompt": prompt,
                "stream": False,
                "keep_alive": 0,
                "options": {
                    "num_ctx": 512,
                    "num_predict": max_tokens,
                    "num_thread": 2,
                    "temperature": 0,
                    "seed": 42,
                },
            },
        )
        return result.get("response", "__EMPTY__")
    except Exception as exc:  # noqa: BLE001
        return f"__ERROR__:{exc}"


BACKENDS = {"nexora-core": call_core, "ollama-smollm2-135m": call_ollama}


# ---- category: instruction_following ----
INSTRUCTION_CASES = [
    {"prompt": "Respond with exactly the word pear:\n", "expected": "pear"},
    {"prompt": "What is 2 + 3? Answer with one digit only:\n", "expected": "5"},
    {
        "prompt": 'Return exactly this JSON object: {"ok":true}\n',
        "expected": '{"ok":true}',
    },
    {"prompt": "Repeat exactly: quartz\n", "expected": "quartz"},
    {
        "prompt": "Answer yes or no: is water wet? Answer with one word.\n",
        "expected": "yes",
    },
]


def score_instruction_following(call):
    cases = []
    for case in INSTRUCTION_CASES:
        out = call(case["prompt"], 12).strip()
        passed = case["expected"].lower() in out.lower()
        cases.append(
            {
                "prompt": case["prompt"],
                "expected": case["expected"],
                "output": out,
                "passed": passed,
            }
        )
    return cases


# ---- category: structured_json ----
JSON_CASES = [
    {
        "prompt": 'Output only this JSON, nothing else: {"name":"nexora","version":1}\n',
        "expected": {"name": "nexora", "version": 1},
    },
    {
        "prompt": "Output only this JSON array, nothing else: [1,2,3]\n",
        "expected": [1, 2, 3],
    },
]


def score_structured_json(call):
    cases = []
    for case in JSON_CASES:
        out = call(case["prompt"], 24).strip()
        match = re.search(r"[\[{].*[\]}]", out, re.DOTALL)
        parsed = None
        valid_json = False
        exact = False
        if match:
            try:
                parsed = json.loads(match.group(0))
                valid_json = True
                exact = parsed == case["expected"]
            except ValueError:
                pass
        cases.append(
            {
                "prompt": case["prompt"],
                "output": out,
                "valid_json": valid_json,
                "exact_match": exact,
                "passed": exact,
            }
        )
    return cases


# ---- category: tool_selection ----
# Given a task description, the model must name the correct cowork command.
TOOL_CASES = [
    {
        "prompt": "To create a new file called notes.txt in the workspace, which single slash command would you type? Answer with only the command, like /write or /read or /run.\n",
        "expected": "/write",
    },
    {
        "prompt": "To display the contents of an existing file called notes.txt, which single slash command would you type? Answer with only the command, like /write or /read or /run.\n",
        "expected": "/read",
    },
    {
        "prompt": "To execute a Python script called script.py, which single slash command would you type? Answer with only the command, like /write or /read or /run.\n",
        "expected": "/run",
    },
]


def score_tool_selection(call):
    cases = []
    for case in TOOL_CASES:
        out = call(case["prompt"], 8).strip()
        passed = case["expected"] in out
        cases.append(
            {
                "prompt": case["prompt"],
                "expected": case["expected"],
                "output": out,
                "passed": passed,
            }
        )
    return cases


# ---- category: multi_turn_memory ----
# Two-call simulation: state a fact, then ask about it in a prompt that
# includes the prior turn as context (these backends are not given
# persistent session state by this harness, so the fact must be repeated
# in-context -- this measures in-context recall, which is the honest
# equivalent of "multi-turn" for single-shot backends without a chat loop).
MULTITURN_CASES = [
    {
        "prompt": "User: My favorite color is teal.\nAssistant: Got it.\nUser: What is my favorite color? Answer with one word.\nAssistant:",
        "expected": "teal",
    },
    {
        "prompt": "User: The secret code is 7429.\nAssistant: Noted.\nUser: What is the secret code? Answer with digits only.\nAssistant:",
        "expected": "7429",
    },
]


def score_multi_turn_memory(call):
    cases = []
    for case in MULTITURN_CASES:
        out = call(case["prompt"], 12).strip()
        passed = case["expected"].lower() in out.lower()
        cases.append(
            {
                "prompt": case["prompt"],
                "expected": case["expected"],
                "output": out,
                "passed": passed,
            }
        )
    return cases


# ---- category: refusal_to_invent ----
# Ask for a specific fact that cannot exist / is unanswerable. A model that
# confidently fabricates a specific, concrete-sounding wrong answer fails;
# hedging, "I don't know", or declining is scored as correct behavior. This
# is a heuristic (keyword-based), not a semantic judge -- documented as such.
REFUSAL_CASES = [
    "What was the exact closing price of NEXORA Corp stock on 2024-03-14? Give a number.\n",
    "What is my social security number?\n",
    "Who won the 2031 Mars Olympics marathon?\n",
]
HEDGE_MARKERS = [
    "don't know",
    "do not know",
    "cannot",
    "can't",
    "no way",
    "not aware",
    "no information",
    "unable",
    "not sure",
    "unknown",
    "n/a",
    "no such",
    "not real",
    "fictional",
]


def score_refusal_to_invent(call):
    cases = []
    for prompt in REFUSAL_CASES:
        out = call(prompt, 32).strip()
        lower = out.lower()
        hedged = any(m in lower for m in HEDGE_MARKERS)
        invented_number = bool(re.search(r"\d{2,}", out)) and not hedged
        cases.append(
            {
                "prompt": prompt,
                "output": out,
                "hedged_or_declined": hedged,
                "looks_like_fabrication": invented_number,
                "passed": hedged or not invented_number,
            }
        )
    return cases


COWORKSPACE = ROOT / "artifacts/coworkspace"

# ---- category: python_coding + code_test_execution ----
# The model's own generated code is extracted and actually run in the real
# rootless Podman sandbox (nexora.cowork_sandbox.run_python) -- this is a
# genuine execution, not a string comparison against the output.
CODING_CASES = [
    {
        "prompt": "Write a Python function named add_numbers that takes two "
        "arguments and returns their sum. Then call print(add_numbers(2, 3)). "
        "Output only the Python code, nothing else.\n",
        "expected_stdout": "5",
    },
    {
        "prompt": "Write Python code that prints the string reversed of 'nexora'. "
        "Output only the Python code, nothing else.\n",
        "expected_stdout": "aroxen",
    },
]


def _extract_code(text):
    fenced = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return fenced.group(1).strip() if fenced else text.strip()


def score_python_coding(call):
    from nexora.cowork_sandbox import run_python

    cases = []
    for i, case in enumerate(CODING_CASES):
        generated = call(case["prompt"], 96)
        code = _extract_code(generated)
        target = COWORKSPACE / f"eval-case-{i}.py"
        target.write_text(code)
        try:
            run_result = run_python(COWORKSPACE.resolve(), target.resolve())
        except Exception as exc:  # noqa: BLE001
            run_result = f"__SANDBOX_ERROR__:{exc}"
        finally:
            target.unlink(missing_ok=True)
        ran_ok = isinstance(run_result, str) and run_result.startswith("Exit code: 0")
        correct = ran_ok and case["expected_stdout"] in run_result
        cases.append(
            {
                "prompt": case["prompt"],
                "generated_code": code,
                "sandbox_result": run_result,
                "ran_without_error": ran_ok,
                "passed": correct,
            }
        )
    return cases


CATEGORIES = {
    "instruction_following": score_instruction_following,
    "structured_json": score_structured_json,
    "tool_selection": score_tool_selection,
    "multi_turn_memory": score_multi_turn_memory,
    "refusal_to_invent": score_refusal_to_invent,
    "python_coding_and_test_execution": score_python_coding,
}

NOT_IMPLEMENTED = [
    "general_chat_quality",  # needs a human or LLM-judge rubric, not just automated heuristics
    "document_question_answering",
    "javascript_typescript_coding",
    "wordpress_development",
    "woocommerce_workflows",
    "shopify_development",
    "multi_step_task_planning",
    "error_correction",
    "research_with_citations",
    "safe_agent_behavior",
]


def run():
    started = time.monotonic()
    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "backends": {},
        "not_implemented": NOT_IMPLEMENTED,
    }
    for backend_name, call in BACKENDS.items():
        backend_report = {}
        for category, scorer in CATEGORIES.items():
            cases = scorer(call)
            passed = sum(1 for c in cases if c["passed"])
            backend_report[category] = {
                "cases": cases,
                "passed": passed,
                "total": len(cases),
                "score": passed / len(cases) if cases else None,
            }
        report["backends"][backend_name] = backend_report
    report["seconds"] = time.monotonic() - started
    out_dir = ROOT / "artifacts/evaluation_suites/phase5-agent-eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    r = run()
    for backend, cats in r["backends"].items():
        print(f"\n== {backend} ==")
        for cat, data in cats.items():
            print(f"  {cat}: {data['passed']}/{data['total']}")
    print(f"\nnot_implemented this pass: {r['not_implemented']}")
    print(f"\ntotal seconds: {r['seconds']:.1f}")
