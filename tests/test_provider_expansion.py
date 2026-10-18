import base64
import io
import wave
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException
from test_api import client  # noqa: F401


def wav(channels=1, width=2, seconds=1):
    out = io.BytesIO()
    with wave.open(out, "wb") as stream:
        stream.setnchannels(channels)
        stream.setsampwidth(width)
        stream.setframerate(16000)
        stream.writeframes(b"\x00" * 16000 * channels * width * seconds)
    return base64.b64encode(out.getvalue()).decode()


def test_speech_consent_key_and_validation(client, monkeypatch):  # noqa: F811
    assert (
        client.post(
            "/api/speech/riva/transcribe", json={"wav_base64": wav()}
        ).status_code
        == 409
    )
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_NIM_API_KEY", raising=False)
    assert (
        client.post(
            "/api/speech/riva/transcribe",
            json={"wav_base64": wav(), "allow_hosted": True},
        ).status_code
        == 503
    )
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    for audio in ["bad!", wav(channels=2), wav(width=1), wav(seconds=31)]:
        assert (
            client.post(
                "/api/speech/riva/transcribe",
                json={"wav_base64": audio, "allow_hosted": True},
            ).status_code
            == 422
        )


def test_speech_transcribe_translate_route(client, monkeypatch):  # noqa: F811
    from nexora import riva_speech

    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    for task in ("transcribe", "translate"):

        def fake(raw, rate, language, requested_task, key):
            assert len(raw) == 32000 and rate == 16000
            assert language == "fr" and requested_task == task and key == "test-key"
            return "Hello"

        monkeypatch.setattr(riva_speech, "recognize", fake)
        r = client.post(
            "/api/speech/riva/transcribe",
            json={
                "wav_base64": wav(),
                "allow_hosted": True,
                "language": "fr",
                "task": task,
            },
        )
        assert r.status_code == 200
        assert r.json()["text"] == "Hello" and r.json()["training_enabled"] is False


def test_real_riva_config_metadata_deadline_and_cleanup(monkeypatch):
    import riva.client
    from nexora.riva_speech import recognize, FUNCTION_ID

    closed = []

    def auth(**kwargs):
        assert kwargs["use_ssl"] is True
        assert kwargs["uri"] == "grpc.nvcf.nvidia.com:443"
        assert kwargs["metadata_args"] == [
            ["function-id", FUNCTION_ID],
            ["authorization", "Bearer test"],
        ]
        return SimpleNamespace(
            channel=SimpleNamespace(close=lambda: closed.append(True)),
            get_auth_metadata=lambda: [("authorization", "Bearer test")],
        )

    def call(request, metadata, timeout):
        assert timeout == 30
        assert request.config.custom_configuration["task"] == "translate"
        assert request.config.encoding == riva.client.AudioEncoding.LINEAR_PCM
        assert request.config.sample_rate_hertz == 16000
        assert request.audio == b"\x00\x00"
        return SimpleNamespace(
            results=[
                SimpleNamespace(alternatives=[SimpleNamespace(transcript="Hello")])
            ]
        )

    monkeypatch.setattr(riva.client, "Auth", auth)
    monkeypatch.setattr(
        riva.client,
        "ASRService",
        lambda a: SimpleNamespace(stub=SimpleNamespace(Recognize=call)),
    )
    assert recognize(b"\x00\x00", 16000, "fr", "translate", "test") == "Hello"
    assert closed == [True]


def test_retired_model_error_is_actionable():
    from nexora.nvidia_nim import _handle

    with pytest.raises(HTTPException) as exc:
        _handle(httpx.Response(410, json={"detail": "Gone"}))
    assert exc.value.status_code == 410 and "retired" in exc.value.detail


def test_catalog_keeps_aliases_separate_from_real_models(client, monkeypatch):  # noqa: F811
    from nexora import model_catalog

    monkeypatch.setattr(
        model_catalog, "fcc_models", lambda: ["ollama/smollm2:135m-instruct-q4_K_M"]
    )
    result = client.get("/api/models/catalog").json()
    assert len(result["fcc"]["providers"]) == 60
    assert len(result["fcc"]["aliases"]) == 8
    assert result["fcc_available_models"] == ["ollama/smollm2:135m-instruct-q4_K_M"]
    assert result["nvidia"][-1]["retired"] is True


def test_opt_in_memory_is_bounded_isolated_and_used(client, monkeypatch):  # noqa: F811
    from nexora import reference

    captured = []

    def fake(path, payload=None):
        if path == "/api/tags":
            return {
                "models": [{"name": reference.MODEL, "digest": reference.MODEL_DIGEST}]
            }
        captured.append(payload)
        return {"done": True, "message": {"content": "OK"}}

    monkeypatch.setattr(reference, "request", fake)
    for project, content in [
        ("local", "Use integer cents"),
        ("other", "secret-other-project"),
    ]:
        client.post(
            "/api/knowledge/entries",
            json={
                "kind": "project",
                "project": project,
                "content": content,
                "provenance": "Owner requirement",
            },
        )
    ident = client.post("/api/cowork/threads").json()["id"]
    url = f"/api/cowork/threads/{ident}/messages"
    result = client.post(url, json={"text": "hello", "use_memory": True}).json()
    assert result["role"] == "assistant" and len(result["memory_ids"]) == 1
    assert "integer cents" in captured[0]["messages"][0]["content"]
    assert "secret-other-project" not in str(captured)
    result = client.post(url, json={"text": "hello"}).json()
    assert result["memory_ids"] == []
    assert all(m["role"] != "system" for m in captured[-1]["messages"])


def test_requested_hosted_models_and_kimi_single_turn(client, monkeypatch):  # noqa: F811
    from nexora import nvidia_nim

    calls = []

    def fake(method, path, json_body):
        calls.append(json_body)
        return {"choices": [{"message": {"content": "OK"}}]}

    monkeypatch.setattr(nvidia_nim, "request", fake)
    ident = client.post("/api/cowork/threads").json()["id"]
    url = f"/api/cowork/threads/{ident}/messages"
    for provider in ("nvidia-gemma-7b", "nvidia-kimi-k3"):
        assert (
            client.post(url, json={"text": "hello", "provider": provider}).json()[
                "role"
            ]
            == "error"
        )
        assert (
            client.post(
                url, json={"text": "hello", "provider": provider, "allow_hosted": True}
            ).json()["role"]
            == "assistant"
        )
    assert calls[0]["model"] == "google/gemma-7b"
    assert calls[1]["model"] == "moonshotai/kimi-k3"
    assert len(calls[1]["messages"]) == 1


def test_fcc_alias_request_and_system_context(monkeypatch):
    import json
    from nexora.local_sidecars import chat

    original = httpx.Client

    def handle(request):
        payload = json.loads(request.content)
        assert payload["model"] == "claude-fable-5"
        assert payload["system"] == "Reference project note"
        assert payload["messages"] == [{"role": "user", "content": "hi"}]
        return httpx.Response(
            200, json={"content": [{"type": "text", "text": "Hello"}]}
        )

    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs),
    )
    assert (
        chat(
            "fcc",
            [
                {"role": "system", "content": "Reference project note"},
                {"role": "user", "content": "hi"},
            ],
            "claude-fable-5",
        )
        == "Hello"
    )
    with pytest.raises(HTTPException) as exc:
        chat("fcc", [], "unknown-model")
    assert exc.value.status_code == 422
