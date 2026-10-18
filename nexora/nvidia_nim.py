"""NVIDIA NIM hosted provider adapter.

Documented OpenAI-compatible REST surface, confirmed from NVIDIA's own published
reference pages rather than an authenticated console:
https://docs.api.nvidia.com/nim/reference/llm-apis and
https://docs.nvidia.com/nim/large-language-models/latest/api-reference.html.

Base URL: https://integrate.api.nvidia.com/v1
Auth: "Authorization: Bearer <key>" where the key is generated at
https://build.nvidia.com and begins with "nvapi-".
Endpoints used here: GET /v1/models, POST /v1/chat/completions,
POST /v1/embeddings, and experimental POST /v1/responses.

Known gotcha (NVIDIA developer forum, verified by live web search during this
project's review, not reproduced locally): a key can be valid for GET /v1/models
and still receive HTTP 403 on /v1/chat/completions when the owning NVIDIA
account/org has not been granted "Public API Endpoints" hosted-inference
access. This module surfaces that distinction instead of collapsing every
failure into one generic error.

Public model discovery has been exercised against the live API without a key.
Hosted generation/streaming/embeddings have not been live-verified because no
NVIDIA_NIM_API_KEY is configured in the current verified environment. `/api/nvidia/status` reports real, current reachability and
never assumes success. Tests mock the HTTP layer via `request`/`stream_request`.

Do not assume every catalog model supports every feature below (tool calling,
vision, embeddings) -- NVIDIA's catalog spans many providers and modalities;
callers must pick a model id they know supports the request they are making.
"""

import json
import os
import time

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

BASE_URL = "https://integrate.api.nvidia.com/v1"
KEY_ENV = "NVIDIA_NIM_API_KEY"
TIMEOUT = 30
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_model_cache = {"data": None, "fetched": 0.0}
MODEL_CACHE_SECONDS = 300


def configured_key():
    """Canonical project variable takes precedence over NVIDIA sample alias."""
    return (
        os.environ.get(KEY_ENV, "").strip()
        or os.environ.get("NVIDIA_API_KEY", "").strip()
    )


def _key():
    key = configured_key()
    if not key:
        raise HTTPException(
            503,
            f"{KEY_ENV} is not set. Obtain your own key at https://build.nvidia.com "
            "and put it in an ignored local environment file or secret store; "
            "never commit it.",
        )
    return key


def request(method, path, json_body=None, require_key=True):
    """Single non-streaming NVIDIA NIM call. Raises HTTPException, never a bare exception.

    GET /v1/models is verified (2026-10-18, live) to work unauthenticated --
    NVIDIA serves the public catalog without a key. Every other endpoint used
    here (chat completions, embeddings) returns 401 without one, confirmed
    the same way.
    """
    headers = {"Accept": "application/json"}
    key = _key() if require_key else configured_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    try:
        with httpx.Client(trust_env=False, timeout=TIMEOUT) as client:
            response = client.request(
                method, BASE_URL + path, json=json_body, headers=headers
            )
    except httpx.HTTPError as exc:
        raise HTTPException(503, f"NVIDIA NIM unreachable: {exc}") from exc
    return _handle(response)


def _handle(response):
    if response.status_code == 401:
        raise HTTPException(
            502, "NVIDIA NIM rejected the API key (401); verify NVIDIA_NIM_API_KEY"
        )
    if response.status_code == 403:
        raise HTTPException(
            502,
            "NVIDIA NIM returned 403. This call is "
            "refused -- commonly because the owning NVIDIA account/org has not "
            "been granted 'Public API Endpoints' hosted-inference access, or "
            "lacks entitlement for this specific model.",
        )
    if response.status_code == 404:
        raise HTTPException(502, "NVIDIA NIM: unknown model id or endpoint (404)")
    if response.status_code == 410:
        raise HTTPException(
            410, "NVIDIA model has been retired; choose another model explicitly"
        )
    if response.status_code == 429:
        raise HTTPException(
            429, "NVIDIA NIM rate limit exceeded; back off and retry later"
        )
    if response.status_code >= 400:
        raise HTTPException(
            502, f"NVIDIA NIM error {response.status_code}: {response.text[:300]}"
        )
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise HTTPException(502, "NVIDIA NIM response exceeded local size limit")
    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(502, "NVIDIA NIM returned a non-JSON response") from exc
    if not isinstance(data, dict):
        raise HTTPException(502, "NVIDIA NIM returned an unexpected response shape")
    return data


def stream_request(path, json_body):
    """Yield raw SSE 'data:' payload strings for a streaming NIM call. Caller parses JSON."""
    headers = {"Authorization": f"Bearer {_key()}", "Accept": "text/event-stream"}
    total = 0
    try:
        with (
            httpx.Client(trust_env=False, timeout=TIMEOUT) as client,
            client.stream(
                "POST", BASE_URL + path, json=json_body, headers=headers
            ) as response,
        ):
            if response.status_code != 200:
                response.read()
                _handle(response)
                return
            for line in response.iter_lines():
                total += len(line)
                if total > MAX_RESPONSE_BYTES:
                    raise HTTPException(
                        502, "NVIDIA NIM stream exceeded local size limit"
                    )
                if not line or not line.startswith("data:"):
                    continue
                payload = line[len("data:") :].strip()
                if payload == "[DONE]":
                    return
                yield payload
    except httpx.HTTPError as exc:
        raise HTTPException(503, f"NVIDIA NIM unreachable: {exc}") from exc


def list_models(force=False):
    now = time.monotonic()
    if (
        not force
        and _model_cache["data"] is not None
        and now - _model_cache["fetched"] < MODEL_CACHE_SECONDS
    ):
        return _model_cache["data"]
    data = request("GET", "/models", require_key=False)
    entries = data.get("data", [])
    if not isinstance(entries, list):
        raise HTTPException(502, "NVIDIA NIM /v1/models returned an unexpected shape")
    models = [
        {"id": m.get("id"), "owned_by": m.get("owned_by")}
        for m in entries
        if isinstance(m, dict) and isinstance(m.get("id"), str)
    ]
    _model_cache["data"] = models
    _model_cache["fetched"] = now
    return models


class ChatMessage(BaseModel):
    role: str = Field(pattern=r"^(system|user|assistant|tool)$")
    content: str = Field(max_length=8000)


class ChatRequest(BaseModel):
    model: str = Field(min_length=1, max_length=200)
    messages: list[ChatMessage] = Field(min_length=1, max_length=50)
    max_tokens: int = Field(default=256, ge=1, le=4096)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, gt=0.0, le=1.0)
    seed: int | None = Field(default=None, ge=0, le=4294967295)
    tools: list[dict] | None = None
    tool_choice: str | dict | None = None


class ResponsesRequest(BaseModel):
    model: str = Field(default="openai/gpt-oss-20b", min_length=1, max_length=200)
    input: str = Field(min_length=1, max_length=32000)
    max_output_tokens: int = Field(default=256, ge=1, le=4096)
    temperature: float = Field(default=1.0, ge=0.0, le=1.0)
    top_p: float = Field(default=1.0, gt=0.0, le=1.0)


class EmbeddingRequest(BaseModel):
    model: str = Field(min_length=1, max_length=200)
    input: list[str] = Field(min_length=1, max_length=32)


def _chat_payload(body: ChatRequest, stream: bool):
    payload = {
        "model": body.model,
        "messages": [m.model_dump() for m in body.messages],
        "max_tokens": body.max_tokens,
        "temperature": body.temperature,
        "top_p": body.top_p,
        "stream": stream,
    }
    if body.seed is not None:
        payload["seed"] = body.seed
    if body.tools:
        payload["tools"] = body.tools
    if body.tool_choice:
        payload["tool_choice"] = body.tool_choice
    return payload


def router(audit):
    routes = APIRouter(prefix="/api/nvidia", tags=["NVIDIA NIM"])

    @routes.get("/status")
    def status():
        key_present = bool(configured_key())
        result = {
            "provider": "NVIDIA NIM",
            "base_url": BASE_URL,
            "key_env": KEY_ENV,
            "key_configured": key_present,
            "reachable": False,
            "model_count": None,
            "detail": None,
            "generation_available": key_present,
        }
        # GET /v1/models is NVIDIA's public, unauthenticated catalog endpoint
        # (verified live 2026-10-18); it works with or without a key, so
        # reachability can be reported honestly even before one is configured.
        try:
            models = list_models(force=True)
            result["reachable"] = True
            result["model_count"] = len(models)
            if not key_present:
                result["detail"] = (
                    f"Model catalog reachable without a key. {KEY_ENV} is not "
                    "set, so chat/embeddings generation will fail; get a key "
                    "at https://build.nvidia.com."
                )
        except HTTPException as exc:
            result["detail"] = exc.detail
        return result

    @routes.get("/models")
    def models():
        return {"provider": "NVIDIA NIM", "models": list_models()}

    @routes.post("/generate")
    def generate(body: ChatRequest):
        payload = _chat_payload(body, stream=False)
        data = request("POST", "/chat/completions", payload)
        choices = data.get("choices", [])
        if not isinstance(choices, list) or not choices:
            raise HTTPException(502, "NVIDIA NIM returned no choices")
        message = choices[0].get("message", {})
        text = message.get("content")
        audit(
            "nvidia.generate",
            json.dumps(
                {
                    "provider": "NVIDIA NIM",
                    "model": body.model,
                    "usage": data.get("usage"),
                }
            ),
        )
        return {
            "provider": "NVIDIA NIM",
            "model": body.model,
            "text": text,
            "tool_calls": message.get("tool_calls"),
            "usage": data.get("usage"),
            "finish_reason": choices[0].get("finish_reason"),
        }

    @routes.post("/responses")
    def responses(body: ResponsesRequest):
        # Opt-in experimental endpoint: never silently route to Chat Completions.
        data = request("POST", "/responses", {**body.model_dump(), "stream": False})
        output = data.get("output")
        if not isinstance(output, list) or data.get("error"):
            raise HTTPException(
                502, "NVIDIA Responses returned an invalid or failed response"
            )
        texts = []
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content = item.get("content", [])
            if not isinstance(content, list):
                raise HTTPException(
                    502, "NVIDIA Responses returned invalid message content"
                )
            for part in content:
                if isinstance(part, dict) and part.get("type") == "output_text":
                    if not isinstance(part.get("text"), str):
                        raise HTTPException(
                            502, "NVIDIA Responses returned invalid output text"
                        )
                    texts.append(part["text"])
        status = data.get("status")
        if status not in ("completed", "incomplete"):
            raise HTTPException(502, "NVIDIA Responses did not complete synchronously")
        audit(
            "nvidia.responses",
            json.dumps(
                {"model": body.model, "usage": data.get("usage"), "status": status}
            ),
        )
        return {
            "provider": "NVIDIA NIM",
            "model": body.model,
            "text": "".join(texts),
            "status": status,
            "usage": data.get("usage"),
            "incomplete_details": data.get("incomplete_details"),
        }

    @routes.post("/stream")
    def stream(body: ChatRequest):
        from fastapi.responses import StreamingResponse

        payload = _chat_payload(body, stream=True)

        def chunks():
            for raw in stream_request("/chat/completions", payload):
                try:
                    event = json.loads(raw)
                except ValueError:
                    continue
                delta = event.get("choices", [{}])[0].get("delta", {}).get("content")
                if delta:
                    yield delta
            audit(
                "nvidia.stream",
                json.dumps({"provider": "NVIDIA NIM", "model": body.model}),
            )

        return StreamingResponse(chunks(), media_type="text/plain")

    @routes.post("/embeddings")
    def embeddings(body: EmbeddingRequest):
        data = request(
            "POST",
            "/embeddings",
            {"model": body.model, "input": body.input},
        )
        vectors = data.get("data", [])
        audit(
            "nvidia.embeddings",
            json.dumps(
                {"provider": "NVIDIA NIM", "model": body.model, "count": len(vectors)}
            ),
        )
        return {"provider": "NVIDIA NIM", "model": body.model, "data": vectors}

    return routes
