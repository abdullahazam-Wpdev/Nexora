"""Public provider metadata and live local FCC discovery; never credentials."""

import json
import httpx
from fastapi import APIRouter, HTTPException
from nexora.config import ROOT

REQUESTED_MODELS = [
    {
        "id": "google/gemma-7b",
        "label": "Gemma 7B",
        "status": "documented; hosted generation unverified",
        "docs": "https://docs.api.nvidia.com/nim/reference/google-gemma-7b",
    },
    {
        "id": "moonshotai/kimi-k3",
        "label": "Kimi K3",
        "status": "single-turn text only; hosted generation unverified",
        "docs": "https://docs.api.nvidia.com/nim/reference/moonshotai-kimi-k3",
    },
    {
        "id": "deepseek-ai/deepseek-v4-flash",
        "label": "DeepSeek V4 Flash",
        "status": "retired per owner-supplied HTTP 410; unavailable",
        "retired": True,
        "retired_at": "2026-08-07T09:00:00Z",
    },
]


def fcc_snapshot():
    return json.loads((ROOT / "catalogs/fcc/catalog.json").read_text())


def fcc_models():
    try:
        with httpx.Client(trust_env=False, timeout=3) as client:
            with client.stream(
                "GET", "http://127.0.0.1:8082/admin/api/models"
            ) as response:
                response.raise_for_status()
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 2 * 1024 * 1024:
                        raise ValueError("Catalog exceeds limit")
        data = json.loads(raw)
        models = data["models"]
        if not isinstance(models, list) or any(not isinstance(m, str) for m in models):
            raise ValueError("Invalid models")
        return models[:5000]
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            503, "Local FCC catalog unavailable; start scripts/fcc.sh"
        ) from exc


def router():
    routes = APIRouter(prefix="/api/models", tags=["model catalogs"])

    @routes.get("/catalog")
    def catalog():
        snapshot = fcc_snapshot()
        try:
            live, error = fcc_models(), None
        except HTTPException as exc:
            live, error = [], exc.detail
        return {
            "nvidia": REQUESTED_MODELS,
            "fcc": snapshot,
            "fcc_available_models": live,
            "fcc_error": error,
            "training_enabled": False,
        }

    return routes
