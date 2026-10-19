"""Correct a vacuous HTML acceptance assertion and rescore actual stored candidates."""

import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nexora.language_sandbox import run
from nexora.config import STORE
from nexora.artifacts import atomic_json

new_test = """from pathlib import Path
from html.parser import HTMLParser
class P(HTMLParser):
 def __init__(self):super().__init__();self.labels=[];self.inputs=[]
 def handle_starttag(self,t,a):
  if t=='label':self.labels.append(dict(a))
  if t=='input':self.inputs.append(dict(a))
p=P();p.feed(Path('index.html').read_text())
assert len(p.labels)==1 and p.labels[0].get('for')=='name'
assert len(p.inputs)==1 and p.inputs[0].get('id')=='name'
"""
path = ROOT / "benchmarks/phase9-acceptance.json"
tests = json.loads(path.read_text())
tests["html-label"]["test"] = new_test
atomic_json(path, tests)
report = []
for source in (ROOT / "docs/evidence/phase9").glob("coding-*.json"):
    if source.name == "coding-constrained-v1.json":
        continue
    data = json.loads(source.read_text())
    if "cases" not in data:
        continue
    for row in data["cases"]:
        if row["case"] != "html-label" or row["status"] == "blocked":
            continue
        folder = STORE / "workspace-code" / row["task_id"]
        task = json.loads((folder / "task.json").read_text())
        if task.get("candidate"):
            stage = folder / "html-rescore"
            stage.mkdir(exist_ok=True)
            (stage / "index.html").write_text(task["candidate"]["index.html"])
            result = run(stage, "html", new_test + "\nprint('HTML_VERIFIED')")
            passed = result.startswith("Exit code: 0\n") and "HTML_VERIFIED" in result
            row["original_grade"] = row["passed"]
            row["passed"] = passed
            row["rescore_reason"] = (
                "Require actual label AND input; previous assertion was vacuously true when neither tag existed"
            )
            report.append(
                {
                    "report": source.name,
                    "mode": row["mode"],
                    "passed": passed,
                    "output": result[-1000:],
                }
            )
    if "summary" in data:
        for mode in data["summary"]:
            data["summary"][mode]["passed"] = sum(
                r["passed"] for r in data["cases"] if r["mode"] == mode
            )
    atomic_json(source, data)
atomic_json(
    ROOT / "docs/evidence/phase9/html-rescore.json",
    {
        "harness_revision": 2,
        "reason": "Acceptance bug correction; no model outputs were regenerated",
        "cases": report,
    },
)
print("HTML rescore completed; false model success removed")
