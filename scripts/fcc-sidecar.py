#!/usr/bin/env python3
"""Start the unmodified AGPL FCC package with project-local state and Ollama only.

Requires .tools/fcc-venv; does not call any FCC client launcher or installer.
"""

import os
from pathlib import Path

root = Path(__file__).resolve().parent.parent
state = root / "artifacts/fcc-state"
state.mkdir(exist_ok=True)
# FCC's path helper joins this value with Path.home(); an absolute path keeps all
# managed state under this project without changing HOME or editing upstream code.
from free_claude_code.config import paths

paths.FCC_CONFIG_DIRNAME = str(state)
# Seed only our isolated schema, so the vendor's legacy migration never scans
# another application's or the owner's old configuration files.
managed = state / ".env"
if not managed.exists():
    managed.write_text("FCC_CONFIG_SCHEMA=1\n")
    managed.chmod(0o600)
for key, value in {
    "HOST": "127.0.0.1",
    "PORT": "8082",
    "FCC_OPEN_BROWSER": "false",
    "MODEL": "ollama/smollm2:135m-instruct-q4_K_M",
    "MODEL_FALLBACKS": "",
    "MODEL_FABLE": "ollama/smollm2:135m-instruct-q4_K_M",
    "MODEL_OPUS": "ollama/smollm2:135m-instruct-q4_K_M",
    "MODEL_SONNET": "ollama/smollm2:135m-instruct-q4_K_M",
    "MODEL_HAIKU": "ollama/smollm2:135m-instruct-q4_K_M",
    "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
    "PROXY_AUTH_ENABLED": "true",
}.items():
    os.environ[key] = value
# Never use a vendor default proxy token; only server-side ignored key material.
keyfile = root / ".secrets/fcc-token"
if not keyfile.exists():
    import secrets

    keyfile.parent.mkdir(exist_ok=True)
    with keyfile.open("x") as stream:
        stream.write(secrets.token_urlsafe(32))
    keyfile.chmod(0o600)
os.environ["ANTHROPIC_AUTH_TOKEN"] = keyfile.read_text().strip()
from free_claude_code.config.loader import ManagedConfigStore
from free_claude_code.runtime.bootstrap import build_asgi_app
import uvicorn

store = ManagedConfigStore()
store.commit({"ANTHROPIC_AUTH_TOKEN": os.environ["ANTHROPIC_AUTH_TOKEN"]})
settings = store.read().settings
if settings.model != "ollama/smollm2:135m-instruct-q4_K_M" or settings.model_fallbacks:
    raise SystemExit("Refusing non-local provider routing")
uvicorn.run(build_asgi_app(settings), host="127.0.0.1", port=8082)
