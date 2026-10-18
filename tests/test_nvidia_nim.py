from fastapi import HTTPException
from test_api import client  # noqa: F401


def test_status_without_key_but_catalog_reachable(client, monkeypatch):  # noqa: F811
    """GET /v1/models is NVIDIA's unauthenticated public catalog (verified live
    2026-10-18); status should report real reachability even with no key."""
    from nexora import nvidia_nim

    monkeypatch.delenv(nvidia_nim.KEY_ENV, raising=False)
    nvidia_nim._model_cache["data"] = None

    def fake(method, path, json_body=None, require_key=True):
        assert require_key is False
        return {"data": [{"id": "meta/llama2-70b", "owned_by": "meta"}]}

    monkeypatch.setattr(nvidia_nim, "request", fake)
    out = client.get("/api/nvidia/status").json()
    assert out["key_configured"] is False
    assert out["reachable"] is True
    assert out["generation_available"] is False
    assert "NVIDIA_NIM_API_KEY" in out["detail"]


def test_status_without_key_and_unreachable(client, monkeypatch):  # noqa: F811
    from nexora import nvidia_nim

    monkeypatch.delenv(nvidia_nim.KEY_ENV, raising=False)
    nvidia_nim._model_cache["data"] = None

    def fake(method, path, json_body=None, require_key=True):
        raise HTTPException(503, "NVIDIA NIM unreachable: timeout")

    monkeypatch.setattr(nvidia_nim, "request", fake)
    out = client.get("/api/nvidia/status").json()
    assert out["key_configured"] is False
    assert out["reachable"] is False
    assert "unreachable" in out["detail"]


def test_status_reachable_with_mocked_key(client, monkeypatch):  # noqa: F811
    from nexora import nvidia_nim

    monkeypatch.setenv(nvidia_nim.KEY_ENV, "nvapi-test")
    nvidia_nim._model_cache["data"] = None

    def fake(method, path, json_body=None, require_key=True):
        assert path == "/models"
        return {"data": [{"id": "meta/llama-3.1-8b-instruct", "owned_by": "meta"}]}

    monkeypatch.setattr(nvidia_nim, "request", fake)
    out = client.get("/api/nvidia/status").json()
    assert out["key_configured"] is True
    assert out["reachable"] is True
    assert out["generation_available"] is True
    assert out["model_count"] == 1

    models = client.get("/api/nvidia/models").json()["models"]
    assert models == [{"id": "meta/llama-3.1-8b-instruct", "owned_by": "meta"}]


def test_status_surfaces_403_distinctly(client, monkeypatch):  # noqa: F811
    from nexora import nvidia_nim

    monkeypatch.setenv(nvidia_nim.KEY_ENV, "nvapi-test")
    nvidia_nim._model_cache["data"] = None

    def fake(method, path, json_body=None, require_key=True):
        raise HTTPException(
            502,
            "NVIDIA NIM returned 403. The key authenticates but this call is refused",
        )

    monkeypatch.setattr(nvidia_nim, "request", fake)
    out = client.get("/api/nvidia/status").json()
    assert out["reachable"] is False
    assert "403" in out["detail"]


def test_generate_requires_key(client, monkeypatch):  # noqa: F811
    from nexora import nvidia_nim

    monkeypatch.delenv(nvidia_nim.KEY_ENV, raising=False)
    out = client.post(
        "/api/nvidia/generate",
        json={
            "model": "meta/llama-3.1-8b-instruct",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert out.status_code == 503


def test_generate_mocked_round_trip(client, monkeypatch):  # noqa: F811
    from nexora import nvidia_nim

    monkeypatch.setenv(nvidia_nim.KEY_ENV, "nvapi-test")
    calls = []

    def fake(method, path, json_body=None):
        calls.append((method, path, json_body))
        return {
            "choices": [
                {
                    "message": {"content": "hello back", "tool_calls": None},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"total_tokens": 5},
        }

    monkeypatch.setattr(nvidia_nim, "request", fake)
    out = client.post(
        "/api/nvidia/generate",
        json={
            "model": "meta/llama-3.1-8b-instruct",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 16,
        },
    )
    assert out.status_code == 200
    body = out.json()
    assert body["text"] == "hello back"
    assert body["usage"] == {"total_tokens": 5}
    assert calls[0][1] == "/chat/completions"
    assert calls[0][2]["stream"] is False
    assert calls[0][2]["max_tokens"] == 16


def test_generate_rejects_oversized_input(client, monkeypatch):  # noqa: F811
    from nexora import nvidia_nim

    monkeypatch.setenv(nvidia_nim.KEY_ENV, "nvapi-test")
    out = client.post(
        "/api/nvidia/generate",
        json={
            "model": "x",
            "messages": [{"role": "user", "content": "a"}] * 51,
        },
    )
    assert out.status_code == 422


def test_embeddings_mocked(client, monkeypatch):  # noqa: F811
    from nexora import nvidia_nim

    monkeypatch.setenv(nvidia_nim.KEY_ENV, "nvapi-test")

    def fake(method, path, json_body=None):
        assert path == "/embeddings"
        return {"data": [{"embedding": [0.1, 0.2]}]}

    monkeypatch.setattr(nvidia_nim, "request", fake)
    out = client.post(
        "/api/nvidia/embeddings",
        json={"model": "nvidia/nv-embed-v2", "input": ["hello"]},
    )
    assert out.status_code == 200
    assert out.json()["data"] == [{"embedding": [0.1, 0.2]}]


def test_stream_yields_delta_text(client, monkeypatch):  # noqa: F811
    from nexora import nvidia_nim

    monkeypatch.setenv(nvidia_nim.KEY_ENV, "nvapi-test")

    def fake_stream(path, json_body):
        assert json_body["stream"] is True
        yield '{"choices": [{"delta": {"content": "Hel"}}]}'
        yield '{"choices": [{"delta": {"content": "lo"}}]}'

    monkeypatch.setattr(nvidia_nim, "stream_request", fake_stream)
    with client.stream(
        "POST",
        "/api/nvidia/stream",
        json={"model": "x", "messages": [{"role": "user", "content": "hi"}]},
    ) as response:
        text = "".join(response.iter_text())
    assert text == "Hello"


def test_alias_and_canonical_precedence(monkeypatch):
    from nexora import nvidia_nim

    monkeypatch.delenv(nvidia_nim.KEY_ENV, raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY", "alias-test")
    assert nvidia_nim._key() == "alias-test"
    monkeypatch.setenv(nvidia_nim.KEY_ENV, "canonical-test")
    assert nvidia_nim._key() == "canonical-test"


def test_chat_user_parameters_and_final_only(client, monkeypatch):  # noqa: F811
    from nexora import nvidia_nim

    def fake(method, path, json_body):
        assert path == "/chat/completions"
        assert json_body["max_tokens"] == 4096
        assert json_body["seed"] == 42
        assert json_body["top_p"] == 1
        return {
            "choices": [{"message": {"content": "9.8", "reasoning_content": "private"}}]
        }

    monkeypatch.setattr(nvidia_nim, "request", fake)
    response = client.post(
        "/api/nvidia/generate",
        json={
            "model": "openai/gpt-oss-20b",
            "messages": [{"role": "user", "content": "compare"}],
            "max_tokens": 4096,
            "seed": 42,
            "top_p": 1,
        },
    )
    assert response.status_code == 200
    assert response.json()["text"] == "9.8"
    assert "private" not in response.text


def test_responses_final_only_and_incomplete(client, monkeypatch):  # noqa: F811
    from nexora import nvidia_nim

    for status in ("completed", "incomplete"):

        def fake(method, path, json_body):
            assert path == "/responses"
            assert json_body["max_output_tokens"] == 4096
            assert json_body["stream"] is False
            return {
                "status": status,
                "output": [
                    {"type": "reasoning", "summary": "private"},
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "9.8"}],
                    },
                ],
                "usage": {"total_tokens": 12},
                "incomplete_details": {"reason": "max_output_tokens"}
                if status == "incomplete"
                else None,
            }

        monkeypatch.setattr(nvidia_nim, "request", fake)
        response = client.post(
            "/api/nvidia/responses",
            json={"input": "compare", "max_output_tokens": 4096},
        )
        assert response.status_code == 200
        assert response.json()["text"] == "9.8"
        assert response.json()["status"] == status
        assert "private" not in response.text


def test_responses_failures_and_bounds(client, monkeypatch):  # noqa: F811
    from nexora import nvidia_nim

    for data in (
        {"output": {}},
        {"status": "failed", "output": []},
        {"status": "completed", "output": [], "error": {"message": "failed"}},
    ):
        monkeypatch.setattr(nvidia_nim, "request", lambda *args: data)
        assert (
            client.post("/api/nvidia/responses", json={"input": "hi"}).status_code
            == 502
        )
    assert (
        client.post(
            "/api/nvidia/responses", json={"input": "hi", "max_output_tokens": 4097}
        ).status_code
        == 422
    )
    assert (
        client.post("/api/nvidia/responses", json={"input": "x" * 32001}).status_code
        == 422
    )


def test_responses_requires_key(client, monkeypatch):  # noqa: F811
    from nexora import nvidia_nim

    monkeypatch.delenv(nvidia_nim.KEY_ENV, raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    assert client.post("/api/nvidia/responses", json={"input": "hi"}).status_code == 503
