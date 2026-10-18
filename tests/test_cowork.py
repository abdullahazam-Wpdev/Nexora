from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from nexora.cowork import router, workspace_path, command


def client(tmp_path):
    app = FastAPI()
    app.include_router(router(tmp_path, lambda _: {"text": "fixture"}))
    return TestClient(app)


def test_edit_truncates_message_and_everything_after(tmp_path):
    c = client(tmp_path)
    ident = c.post("/api/cowork/threads").json()["id"]
    url = f"/api/cowork/threads/{ident}"
    c.post(url + "/messages", json={"text": "/help"})
    c.post(url + "/messages", json={"text": "/help"})
    before = c.get(url).json()
    assert len(before) == 4  # 2 user + 2 assistant turns
    edited_id = before[2]["id"]  # the second user message
    assert c.delete(f"{url}/messages/{edited_id}").status_code == 204
    after = c.get(url).json()
    assert len(after) == 2
    assert after[-1]["id"] < edited_id


def test_delete_rejects_unknown_message_or_thread(tmp_path):
    c = client(tmp_path)
    ident = c.post("/api/cowork/threads").json()["id"]
    assert c.delete(f"/api/cowork/threads/{ident}/messages/9999").status_code == 404
    assert c.delete("/api/cowork/threads/not-real/messages/1").status_code == 404


def test_restart_persistence_and_tools(tmp_path):
    c = client(tmp_path)
    ident = c.post("/api/cowork/threads").json()["id"]
    url = f"/api/cowork/threads/{ident}"
    result = c.post(
        url + "/messages", json={"text": "/write hello.txt\nhello workspace"}
    )
    assert result.json()["provider"] == "workspace-tool"
    assert (tmp_path / "coworkspace/hello.txt").read_text() == "hello workspace"
    c = client(tmp_path)
    assert len(c.get(url).json()) == 2
    assert (
        c.post(url + "/messages", json={"text": "/read hello.txt"}).json()["text"]
        == "hello workspace"
    )
    assert (
        c.post(url + "/messages", json={"text": "/write hello.txt\noverwrite"}).json()[
            "role"
        ]
        == "error"
    )
    assert (tmp_path / "coworkspace/hello.txt").read_text() == "hello workspace"


def test_boundaries(tmp_path):
    for path in ["../secret", "/etc/passwd", ".env", "folder/../../secret"]:
        with pytest.raises(ValueError):
            workspace_path(tmp_path, path)
    (tmp_path / "outside").symlink_to("/etc")
    with pytest.raises(ValueError):
        workspace_path(tmp_path, "outside/passwd")
    assert not command("/files", tmp_path, Path("unused")).startswith("outside")


def test_no_silent_sidecar_fallback(tmp_path, monkeypatch):
    from fastapi import HTTPException
    import nexora.local_sidecars

    def unavailable(*args):
        raise HTTPException(503, "sidecar unavailable")

    monkeypatch.setattr(nexora.local_sidecars, "chat", unavailable)
    c = client(tmp_path)
    ident = c.post("/api/cowork/threads").json()["id"]
    response = c.post(
        f"/api/cowork/threads/{ident}/messages",
        json={"text": "hello", "provider": "fcc"},
    )
    assert response.json()["role"] == "error"
    assert response.json()["training_enabled"] is False
    assert c.get("/api/cowork/threads/missing").status_code == 404


def test_real_stdio_mcp(tmp_path):
    import json
    import os
    import subprocess
    import sys

    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "workspace_create",
                "arguments": {"path": "mcp.txt", "text": "real stdio"},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "workspace_read", "arguments": {"path": "mcp.txt"}},
        },
    ]
    result = subprocess.run(
        [sys.executable, "-m", "nexora.cowork_mcp"],
        input="\n".join(json.dumps(m) for m in messages) + "\n",
        text=True,
        capture_output=True,
        check=True,
        env={**os.environ, "NEXORA_STORAGE": str(tmp_path)},
        timeout=10,
    )
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(rows) == 4
    assert len(rows[1]["result"]["tools"]) == 4
    assert rows[-1]["result"]["content"][0]["text"] == "real stdio"
