"""Small reproducible diagnostic probes; actual providers, no simulated model scores."""

from pathlib import Path
import sys
import tempfile
import time
import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nexora.artifacts import atomic_json
from nexora.generation_eval import INSTRUCTIONS
from nexora.document_index import initialize, ingest, search, Document

out = ROOT / "docs/evidence/phase8/quality-evaluation.json"
report = {
    "protocol": "Four disclosed exact-output diagnostics plus one two-turn recall, not a professional benchmark",
    "ollama": [],
    "hosted": {"status": "not run; no configured NVIDIA credential"},
    "retrieval": [],
}
started = time.monotonic()
with httpx.Client(timeout=20, trust_env=False) as client:
    for case in INSTRUCTIONS:
        r = client.post(
            "http://127.0.0.1:11434/api/chat",
            json={
                "model": "smollm2:135m-instruct-q4_K_M",
                "messages": [{"role": "user", "content": case["prompt"]}],
                "stream": False,
                "keep_alive": 0,
                "options": {
                    "num_ctx": 768,
                    "num_predict": 32,
                    "num_thread": 2,
                    "temperature": 0,
                    "seed": 42,
                },
            },
        )
        r.raise_for_status()
        text = r.json()["message"]["content"]
        report["ollama"].append(
            {**case, "generated": text, "passed": text.strip() == case["expected"]}
        )
    messages = [
        {"role": "user", "content": "Remember the project code word: quartz."},
        {"role": "assistant", "content": "The project code word is quartz."},
        {
            "role": "user",
            "content": "What is the code word? Reply with only that word.",
        },
    ]
    r = client.post(
        "http://127.0.0.1:11434/api/chat",
        json={
            "model": "smollm2:135m-instruct-q4_K_M",
            "messages": messages,
            "stream": False,
            "keep_alive": 0,
            "options": {
                "num_ctx": 768,
                "num_predict": 32,
                "num_thread": 2,
                "temperature": 0,
                "seed": 42,
            },
        },
    )
    r.raise_for_status()
    text = r.json()["message"]["content"]
    report["multi_turn"] = {
        "history": "one supplied user/assistant exchange, not a measured first-turn answer",
        "generated": text,
        "passed": text.strip() == "quartz",
    }
with tempfile.TemporaryDirectory() as temporary:
    store = Path(temporary)
    initialize(store)
    fixtures = [
        ("Money", "Compute cart totals with integer cents.", "integer cents"),
        (
            "Network",
            "Configure request_timeout for bounded external fetches.",
            "request_timeout",
        ),
        ("Inventory", "Stock levels update after confirmed purchases.", "stock levels"),
    ]
    ids = []
    for title, text, q in fixtures:
        ids.append(
            ingest(store, Document(title=title, text=text, source="urn:test:" + title))[
                "id"
            ]
        )
    for (title, text, q), ident in zip(fixtures, ids):
        hits = search(store, "local", q)
        report["retrieval"].append(
            {
                "query": q,
                "top1_correct": bool(hits and hits[0]["doc_id"] == ident),
                "citation_exact": bool(hits and hits[0]["text"] in text),
                "namespace_isolated": not search(store, "other", q),
            }
        )
report["ollama_passed"] = sum(r["passed"] for r in report["ollama"])
report["seconds"] = time.monotonic() - started
atomic_json(out, report)
print(
    "Ollama exact outputs:",
    report["ollama_passed"],
    "/4; recall:",
    report["multi_turn"]["passed"],
    "retrieval:",
    sum(r["top1_correct"] for r in report["retrieval"]),
    "/3",
)
