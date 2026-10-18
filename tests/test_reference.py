from test_api import client  # noqa: F401


def test_reference_bounds_and_identity(client, monkeypatch):  # noqa: F811
    from nexora import reference

    calls = []

    def fake(path, payload=None):
        calls.append((path, payload))
        if path == "/api/tags":
            return {
                "models": [{"name": reference.MODEL, "digest": reference.MODEL_DIGEST}]
            }
        return {"done": True, "response": "Hello", "eval_count": 1}

    monkeypatch.setattr(reference, "request", fake)
    assert client.get("/api/reference/status").json()["installed"]
    out = client.post("/api/reference/generate", json={"prompt": "Hello"})
    assert out.status_code == 200
    assert out.json()["origin"] == "external open-weight reference"
    assert out.json()["training_enabled"] is False
    assert calls[-1][1]["keep_alive"] == 0
    assert calls[-1][1]["options"]["num_ctx"] == 512
    assert (
        client.post(
            "/api/reference/generate", json={"prompt": "a", "max_tokens": 129}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/reference/generate",
            headers={"Origin": "https://evil.example"},
            json={"prompt": "a"},
        ).status_code
        == 403
    )


def test_reference_serialization_and_failed_release(client, monkeypatch):  # noqa: F811
    from nexora import reference
    from fastapi import HTTPException

    reference._lock.acquire()
    try:
        assert (
            client.post("/api/reference/generate", json={"prompt": "a"}).status_code
            == 429
        )
    finally:
        reference._lock.release()

    def unavailable(*args):
        raise HTTPException(503, "Unavailable")

    monkeypatch.setattr(reference, "request", unavailable)
    assert (
        client.post("/api/reference/generate", json={"prompt": "a"}).status_code == 503
    )
    assert reference._lock.acquire(blocking=False)
    reference._lock.release()


def test_reference_rejects_retagged_model(client, monkeypatch):  # noqa: F811
    from nexora import reference

    monkeypatch.setattr(
        reference,
        "request",
        lambda *args: {"models": [{"name": reference.MODEL, "digest": "wrong"}]},
    )
    assert not client.get("/api/reference/status").json()["installed"]
    assert (
        client.post("/api/reference/generate", json={"prompt": "a"}).status_code == 409
    )


def test_reference_transport_rejects_invalid_and_oversize(monkeypatch):
    import io
    import pytest
    from fastapi import HTTPException
    from nexora import reference

    class FakeOpener:
        def __init__(self, content):
            self.content = content

        def open(self, *args, **kwargs):
            return io.BytesIO(self.content)

    for content in [b"[]", b"not-json", b"x" * (1024 * 1024 + 1)]:
        monkeypatch.setattr(reference, "_opener", FakeOpener(content))
        with pytest.raises(HTTPException) as error:
            reference.request("/api/tags")
        assert error.value.status_code == 503
