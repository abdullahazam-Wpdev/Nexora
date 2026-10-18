"""Real local provider, runtime switching, and persistent chat integration checks."""

import json
import time
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parent.parent
rows = []
with httpx.Client(base_url="http://127.0.0.1:8000", trust_env=False, timeout=70) as c:
    for provider in ["localai", "fcc", "ollama", "core"]:
        if provider != "core":
            r = c.post("/api/cowork/runtime", json={"provider": provider})
            r.raise_for_status()
            assert r.json()["ready"]
        ident = c.post("/api/cowork/threads").json()["id"]
        start = time.monotonic()
        r = c.post(
            f"/api/cowork/threads/{ident}/messages",
            json={"text": "Say hello briefly.", "provider": provider},
        )
        r.raise_for_status()
        payload = r.json()
        assert payload["role"] == "assistant", payload
        assert payload["training_enabled"] is False
        rows.append(
            {
                "provider": provider,
                "thread": ident,
                "result": payload,
                "seconds": time.monotonic() - start,
            }
        )
        assert len(c.get(f"/api/cowork/threads/{ident}").json()) == 2
    bad = c.post("/api/cowork/threads", headers={"Origin": "https://evil.example"})
    assert bad.status_code == 403
folder = ROOT / "artifacts/cowork-verification"
folder.mkdir(exist_ok=True)
(folder / "live-providers.json").write_text(json.dumps(rows, indent=2))
print(json.dumps(rows, indent=2))
