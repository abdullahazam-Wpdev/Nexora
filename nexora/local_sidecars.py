"""Fixed local sidecar clients; credentials and endpoints never come from a prompt."""

from fastapi import HTTPException
from nexora.config import ROOT
import httpx


def chat(provider, messages):
    if provider == "localai":
        url = "http://127.0.0.1:8080/v1/chat/completions"
        headers = {}
        payload = {
            "model": "smollm2-localai",
            "messages": messages,
            "max_tokens": 320,
            "temperature": 0,
            "stream": False,
        }
    elif provider == "fcc":
        token = ROOT / ".secrets/fcc-token"
        if not token.exists():
            raise HTTPException(503, "FCC sidecar is not initialized")
        url = "http://127.0.0.1:8082/v1/messages"
        headers = {
            "x-api-key": token.read_text().strip(),
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": "claude-haiku-4-5",
            "messages": messages,
            "max_tokens": 320,
            "temperature": 0,
            "stream": False,
        }
    else:
        raise ValueError("Unknown sidecar")
    try:
        with httpx.Client(trust_env=False, timeout=120) as client:
            with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                raw = bytearray()
                for block in response.iter_bytes():
                    raw.extend(block)
                    if len(raw) > 1024 * 1024:
                        raise ValueError("Response exceeds limit")
        import json

        data = json.loads(raw)
        if provider == "localai":
            text = data["choices"][0]["message"]["content"]
        else:
            text = "\n".join(
                b["text"] for b in data["content"] if b.get("type") == "text"
            )
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Empty reply")
        return text
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise HTTPException(
            503,
            f"{provider} sidecar unavailable or invalid reply; check its local runtime log",
        ) from exc
