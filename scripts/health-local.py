"""Read-only bounded service checks; emits no credentials or private conversation data."""

import json
import httpx

checks = {}
with httpx.Client(timeout=3, trust_env=False) as client:
    for name, url in {
        "api": "http://127.0.0.1:8000/openapi.json",
        "ui": "http://127.0.0.1:3001",
        "ollama": "http://127.0.0.1:11434/api/tags",
        "fcc": "http://127.0.0.1:8082/health",
    }.items():
        try:
            checks[name] = {"status": client.get(url).status_code}
        except httpx.HTTPError:
            checks[name] = {"status": "unreachable"}
print(json.dumps(checks, indent=2))
raise SystemExit(0 if all(v["status"] == 200 for v in checks.values()) else 1)
