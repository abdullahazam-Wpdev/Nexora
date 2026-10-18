import json
from pathlib import Path
import sys
import time
import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nexora.config import STORE

repo = STORE / "phase7/acceptance-repository"
repo.mkdir(parents=True, exist_ok=True)
(repo / "solution.py").write_text("def add(a,b):\n    return None\n")
report = {}
with httpx.Client(
    base_url="http://127.0.0.1:8000", trust_env=False, timeout=75
) as client:
    reg = client.post("/api/agent/repositories", json={"path": str(repo)})
    reg.raise_for_status()
    task = client.post(
        "/api/agent/tasks",
        json={
            "repository_id": reg.json()["id"],
            "path": "solution.py",
            "goal": "Implement add(a,b) as a pure Python function. Required behavior: a+b. Preserve the function name.",
            "acceptance": "assert add(2,3)==5 and add(-2,2)==0",
            "documentation_url": "https://docs.python.org/3/library/operator.html",
            "provider": "ollama",
            "max_attempts": 2,
        },
    )
    task.raise_for_status()
    ident = task.json()["id"]
    deadline = time.monotonic() + 100
    while time.monotonic() < deadline:
        result = client.get("/api/agent/tasks/" + ident).json()
        if result["status"] not in ["queued", "running"]:
            break
        time.sleep(0.5)
    report["task"] = result
    if result["status"] == "awaiting_approval":
        assert "return None" in (repo / "solution.py").read_text()
        bad = client.post(
            "/api/agent/tasks/" + ident + "/approve",
            json={"candidate_sha256": "incorrect"},
        )
        assert bad.status_code == 409
        approved = client.post(
            "/api/agent/tasks/" + ident + "/approve",
            json={"candidate_sha256": result["candidate_sha256"]},
        )
        approved.raise_for_status()
        report["approved"] = approved.json()
    else:
        report["coding_blocker"] = result.get("error")
    thread = client.post("/api/cowork/threads").json()["id"]
    reply = client.post(
        f"/api/cowork/threads/{thread}/messages",
        json={"text": "Say hello briefly.", "provider": "ollama"},
    )
    reply.raise_for_status()
    report["chat"] = reply.json()
    research = client.post(
        "/api/research/ask",
        json={
            "question": "Python programming language",
            "providers": ["wikipedia"],
            "read_top": True,
        },
    )
    research.raise_for_status()
    report["research"] = research.json()
    report["models"] = client.get("/api/nvidia/openai-models").json()
    report["agent_history_count"] = len(client.get("/api/agent/tasks").json())
(STORE / "phase7/live-acceptance.json").write_text(json.dumps(report, indent=2))
print(
    json.dumps(
        {
            "task_status": result["status"],
            "approved": report.get("approved", {}).get("status"),
            "chat_provider": report["chat"].get("provider"),
            "research_status": report["research"].get("status"),
            "citations": len(report["research"].get("citations", [])),
        },
        indent=2,
    )
)
