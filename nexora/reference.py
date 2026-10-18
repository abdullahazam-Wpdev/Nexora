"""Bounded local reference inference; never selects or trains NEXORA Core."""

import json
import threading
from urllib.error import HTTPError, URLError
from urllib.request import Request, ProxyHandler, build_opener

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

BASE_URL = "http://127.0.0.1:11434"
MODEL = "smollm2:135m-instruct-q4_K_M"
MODEL_DIGEST = "fd316850965252d917ac2bf811adef10ba91e129e5f2809f2a24a8501ff73e4f"
_lock = threading.Lock()
_opener = build_opener(ProxyHandler({}))


def request(path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = Request(
        BASE_URL + path, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with _opener.open(req, timeout=150 if data else 3) as response:
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("Reference response exceeded 1 MiB")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError("Expected an object")
        return result
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        raise HTTPException(
            503, "Local Ollama reference runtime unavailable or returned invalid data"
        ) from exc


class ReferencePrompt(BaseModel):
    prompt: str = Field(min_length=1, max_length=1500)
    max_tokens: int = Field(default=32, ge=1, le=400)


def router(audit):
    routes = APIRouter(prefix="/api/reference", tags=["external reference models"])

    @routes.get("/status")
    def status():
        models = request("/api/tags")
        entries = models.get("models", [])
        if not isinstance(entries, list) or any(
            not isinstance(m, dict) for m in entries
        ):
            raise HTTPException(503, "Invalid local reference model inventory")
        return {
            "provider": "Ollama",
            "origin": "external open-weight reference",
            "model": MODEL,
            "digest": MODEL_DIGEST,
            "installed": any(
                m.get("name") == MODEL and m.get("digest") == MODEL_DIGEST
                for m in entries
            ),
            "training_enabled": False,
        }

    @routes.post("/generate")
    def generate(body: ReferencePrompt):
        if not _lock.acquire(blocking=False):
            raise HTTPException(429, "One reference generation is already running")
        try:
            if not status()["installed"]:
                raise HTTPException(
                    409, "Pinned reference model is missing or its digest changed"
                )
            result = request(
                "/api/generate",
                {
                    "model": MODEL,
                    "prompt": body.prompt,
                    "stream": False,
                    "keep_alive": 0,
                    "options": {
                        "num_ctx": 768,
                        "num_predict": body.max_tokens,
                        "num_thread": 2,
                        "temperature": 0,
                        "seed": 42,
                    },
                },
            )
            if not result.get("done") or not isinstance(result.get("response"), str):
                raise HTTPException(503, "Incomplete reference generation")
            audit(
                "reference.generate",
                json.dumps(
                    {
                        "provider": "Ollama",
                        "model": MODEL,
                        "generated_tokens": result.get("eval_count"),
                    }
                ),
            )
            return {
                "provider": "Ollama",
                "origin": "external open-weight reference",
                "model": MODEL,
                "text": result["response"],
                "training_enabled": False,
                "metrics": {
                    k: result.get(k)
                    for k in (
                        "eval_count",
                        "eval_duration",
                        "load_duration",
                        "total_duration",
                    )
                },
            }
        finally:
            _lock.release()

    return routes
