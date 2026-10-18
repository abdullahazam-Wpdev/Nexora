"""Bounded, explicitly consented NVIDIA hosted Whisper gRPC client."""

import base64
import importlib.util
import io
import wave
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from nexora.nvidia_nim import _key, configured_key

SERVER = "grpc.nvcf.nvidia.com:443"
FUNCTION_ID = "b702f636-f60c-4a3d-a6f4-f3568c13bd7d"


class RivaAudio(BaseModel):
    wav_base64: str = Field(min_length=1, max_length=2_800_000)
    language: str = Field(default="en", pattern=r"^[A-Za-z]{2,3}(-[A-Za-z]{2,4})?$")
    task: str = Field(default="transcribe", pattern="^(transcribe|translate)$")
    allow_hosted: bool = False


def recognize(raw, rate, language, task, key):
    import riva.client
    import grpc

    auth = riva.client.Auth(
        use_ssl=True,
        uri=SERVER,
        metadata_args=[
            ["function-id", FUNCTION_ID],
            ["authorization", "Bearer " + key],
        ],
    )
    try:
        service = riva.client.ASRService(auth)
        config = riva.client.RecognitionConfig(
            encoding=riva.client.AudioEncoding.LINEAR_PCM,
            language_code=language,
            sample_rate_hertz=rate,
            audio_channel_count=1,
            max_alternatives=1,
            enable_automatic_punctuation=True,
        )
        if task == "translate":
            riva.client.add_custom_configuration_to_config(config, "task:translate")
        response = service.stub.Recognize(
            riva.client.proto.riva_asr_pb2.RecognizeRequest(audio=raw, config=config),
            metadata=auth.get_auth_metadata(),
            timeout=30,
        )
        text = "\n".join(
            result.alternatives[0].transcript
            for result in response.results
            if result.alternatives
        )
        if len(text) > 65536:
            raise HTTPException(502, "Transcript exceeds limit")
        return text
    except grpc.RpcError as exc:
        # Status only: upstream details may contain credentials or audio-derived text.
        raise HTTPException(
            503, f"NVIDIA speech request failed: {exc.code().name}"
        ) from exc
    finally:
        auth.channel.close()


def router():
    routes = APIRouter(prefix="/api/speech/riva", tags=["NVIDIA hosted speech"])

    @routes.get("/status")
    def status():
        return {
            "installed": importlib.util.find_spec("riva") is not None,
            "key_configured": bool(configured_key()),
            "server": SERVER,
            "function_id": FUNCTION_ID,
            "generation_verified": False,
        }

    @routes.post("/transcribe")
    def transcribe(body: RivaAudio):
        if not body.allow_hosted:
            raise HTTPException(
                409, "Explicit consent is required to send audio to NVIDIA"
            )
        key = _key()
        try:
            raw = base64.b64decode(body.wav_base64, validate=True)
            if len(raw) > 2_000_000:
                raise ValueError("Audio exceeds limit")
            with wave.open(io.BytesIO(raw)) as audio:
                rate = audio.getframerate()
                if (
                    audio.getnchannels() != 1
                    or audio.getsampwidth() != 2
                    or not 8000 <= rate <= 48000
                    or not 0 < audio.getnframes() / rate <= 30
                ):
                    raise ValueError("Use 16-bit mono WAV up to 30 seconds")
                pcm = audio.readframes(audio.getnframes())
                if len(pcm) != audio.getnframes() * 2:
                    raise ValueError("Truncated WAV")
        except (ValueError, wave.Error, EOFError) as exc:
            raise HTTPException(
                422, "Use a valid 16-bit mono WAV, 8–48 kHz, up to 30 seconds and 2 MB"
            ) from exc
        try:
            text = recognize(pcm, rate, body.language, body.task, key)
        except ImportError as exc:
            raise HTTPException(
                503, "Install the optional speech dependencies first"
            ) from exc
        return {
            "text": text,
            "task": body.task,
            "provider": "NVIDIA hosted Whisper Large V3 (Riva)",
            "training_enabled": False,
        }

    return routes
