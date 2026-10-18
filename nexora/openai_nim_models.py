"""The two distinct models on NVIDIA's OpenAI publisher page, reviewed 2026-10-18."""

import base64
import io
import os

import wave
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nexora.nvidia_nim import configured_key

MODELS = [
    {
        "id": "openai/gpt-oss-20b",
        "provider": "nvidia-nim",
        "publisher": "OpenAI",
        "modality": "text",
        "chat": True,
        "coding": "documented, not locally benchmarked",
        "tools": "documented; task acceptance still required",
        "structured_output": "not verified here",
        "context_limit": 131072,
        "local_requirements": "Beyond this 7.5 GiB laptop; no weights downloaded",
        "endpoint": "https://integrate.api.nvidia.com/v1/chat/completions",
        "docs": "https://build.nvidia.com/openai/gpt-oss-20b",
        "quota": "Account-specific; no unlimited/free guarantee",
        "training": False,
    },
    {
        "id": "openai/whisper-large-v3",
        "provider": "NVIDIA Speech NIM",
        "publisher": "OpenAI",
        "modality": "audio-to-text",
        "chat": False,
        "coding": False,
        "tools": False,
        "context_limit": None,
        "local_requirements": "Separate Speech NIM deployment; not installed on this CPU laptop",
        "endpoint": "/v1/audio/transcriptions on a configured ASR service, not the LLM chat endpoint",
        "docs": "https://docs.nvidia.com/nim/speech/26.05.0/reference/api-references/asr/http-asr.html",
        "quota": "Deployment/account-specific",
        "training": False,
    },
]


class Audio(BaseModel):
    wav_base64: str = Field(min_length=1, max_length=2_800_000)
    language: str = Field(default="en-US", pattern="^[A-Za-z]{2,3}(-[A-Za-z]{2,4})?$")


def router():
    routes = APIRouter(tags=["OpenAI models via NVIDIA"])

    @routes.get("/api/nvidia/openai-models")
    def models():
        return {
            "models": MODELS,
            "chat_key_configured": bool(configured_key()),
            "whisper_configured": os.environ.get("NEXORA_WHISPER_BASE")
            == "http://127.0.0.1:9000",
            "weights_installed": False,
        }

    @routes.post("/api/speech/transcribe")
    def transcribe(body: Audio):
        if os.environ.get("NEXORA_WHISPER_BASE") != "http://127.0.0.1:9000":
            raise HTTPException(
                503,
                "Whisper needs a separately configured Speech NIM service at 127.0.0.1:9000; it is not a chat model or installed on this laptop",
            )
        try:
            raw = base64.b64decode(body.wav_base64, validate=True)
            if len(raw) > 2_000_000:
                raise ValueError("Audio exceeds 2 MB")
            with wave.open(io.BytesIO(raw)) as audio:
                if (
                    audio.getnframes() / audio.getframerate() > 30
                    or audio.getnchannels() != 1
                ):
                    raise ValueError("Use mono WAV up to 30 seconds")
        except (ValueError, wave.Error, EOFError) as exc:
            raise HTTPException(422, "Invalid or oversized mono WAV input") from exc
        try:
            with httpx.Client(trust_env=False, timeout=30) as client:
                result = client.post(
                    "http://127.0.0.1:9000/v1/audio/transcriptions",
                    files={"file": ("audio.wav", raw, "audio/wav")},
                    data={"language": body.language, "model": "whisper-large-v3"},
                )
                result.raise_for_status()
                if len(result.content) > 65536:
                    raise ValueError("ASR response exceeds limit")
                text = result.json()["text"]
                if not isinstance(text, str):
                    raise ValueError("Invalid transcript")
            return {
                "text": text,
                "provider": "Whisper Large V3 / configured Speech NIM",
                "training_enabled": False,
            }
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise HTTPException(
                503, "Configured Whisper service unavailable or returned invalid data"
            ) from exc

    return routes
