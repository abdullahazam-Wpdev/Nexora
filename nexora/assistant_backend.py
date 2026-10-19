"""Explicit pinned offline assistant choices sharing one capped Ollama service."""

import json
import time
import httpx
import psutil
from fastapi import HTTPException
from nexora.config import ROOT
from nexora import reference

MODELS = {"smollm2": reference.MODEL, "qwen-coder": "qwen2.5-coder:0.5b"}


from nexora.compute_budget import compute_job


@compute_job('inference')
def generate(
    model_key, messages, max_tokens=256, stream_callback=None, output_schema=None
):
    if model_key not in MODELS:
        raise ValueError("Unknown approved assistant model")
    if not 1 <= max_tokens <= 512:
        raise ValueError("Token budget exceeded")
    if psutil.virtual_memory().available < 400 * 1024**2:
        raise HTTPException(503, "Insufficient available RAM; postpone inference")
    context = 768
    effective_tokens = max_tokens
    if model_key == "qwen-coder":
        context = 512
        effective_tokens = min(max_tokens, 128)
        profile = ROOT / "artifacts/phase9/evaluation-profile.json"
        if profile.exists():
            spec = json.loads(profile.read_text())
            if spec.get("expires_at", 0) > time.time():
                context = 1024
                effective_tokens = min(max_tokens, 256)
        if len(json.dumps(messages)) > context * 3:
            raise HTTPException(
                422, "Context exceeds the active small-model profile; shorten this task"
            )
    if not reference._lock.acquire(blocking=False):
        raise HTTPException(429, "Local inference busy")
    started = time.monotonic()
    first = None
    text = []
    last = {}
    try:
        with httpx.Client(trust_env=False, timeout=30) as client:
            tags = client.get("http://127.0.0.1:11434/api/tags")
            tags.raise_for_status()
            entries = tags.json().get("models", [])
            if not any(m.get("name") == MODELS[model_key] for m in entries):
                raise HTTPException(
                    503,
                    "Selected model is not installed; no automatic download/fallback",
                )
            if model_key == "smollm2" and not any(
                m.get("name") == reference.MODEL
                and m.get("digest") == reference.MODEL_DIGEST
                for m in entries
            ):
                raise HTTPException(409, "Pinned SmolLM2 digest changed")
            if model_key == "qwen-coder":
                p = ROOT / "tooling/reference/qwen-coder.json"
                if not p.exists():
                    raise HTTPException(503, "Qwen manifest has not been verified")
                manifest = json.loads(p.read_text())
                if manifest.get("enabled") is False:
                    raise HTTPException(
                        503, manifest.get("disabled_reason", "Qwen evaluation disabled")
                    )
                expected = manifest["digest"]
                if not any(
                    m.get("name") == MODELS[model_key] and m.get("digest") == expected
                    for m in entries
                ):
                    raise HTTPException(409, "Pinned Qwen model digest changed")
            with client.stream(
                "POST",
                "http://127.0.0.1:11434/api/chat",
                json={
                    "model": MODELS[model_key],
                    **({"format": output_schema} if output_schema is not None else {}),
                    "messages": messages,
                    "stream": True,
                    "keep_alive": 0,
                    "options": {
                        "num_ctx": context,
                        "num_predict": effective_tokens,
                        "num_thread": 2,
                        "num_batch": 16,
                        "temperature": 0,
                        "seed": 42,
                    },
                },
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if time.monotonic() - started > 45:
                        raise HTTPException(504, "Assistant wall-time budget exhausted")
                    if len(line) > 131072:
                        raise ValueError("Response frame exceeded limit")
                    row = json.loads(line)
                    if not isinstance(row, dict) or not isinstance(
                        row.get("message", {}), dict
                    ):
                        raise ValueError("Invalid stream frame")
                    if row.get("error"):
                        raise ValueError("Ollama generation failed")
                    delta = row.get("message", {}).get("content", "")
                    if not isinstance(delta, str):
                        raise ValueError("Invalid text delta")
                    if delta:
                        if first is None:
                            first = time.monotonic() - started
                        text.append(delta)
                        if sum(map(len, text)) > 32000:
                            raise ValueError("Output budget exceeded")
                        if stream_callback:
                            stream_callback(delta)
                    if row.get("done"):
                        last = row
        if not last or not "".join(text).strip():
            raise ValueError("Incomplete streamed response")
        return {
            "text": "".join(text),
            "model": MODELS[model_key],
            "origin": "external open-weight reference",
            "ttft_seconds": first,
            "seconds": time.monotonic() - started,
            "tokens_per_second": last.get("eval_count", 0)
            / (last["eval_duration"] / 1e9)
            if isinstance(last.get("eval_duration"), (int, float))
            and last["eval_duration"] > 0
            else None,
            "eval_count": last.get("eval_count"),
            "eval_duration": last.get("eval_duration"),
            "effective_max_tokens": effective_tokens,
            "context": context,
        }
    except (httpx.HTTPError, ValueError) as exc:
        if str(exc) == "Owner stopped streaming":
            raise HTTPException(499, "Owner cancelled local generation") from exc
        raise HTTPException(
            503, "Local assistant unavailable or invalid/incomplete response"
        ) from exc
    finally:
        reference._lock.release()
