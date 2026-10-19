import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from nexora.tool_protocol import validate_call, fixtures, router as tools_router
from nexora.workspace_code import Task, create, execute, approve, save, rollback
from nexora.agent_runtime import register
from nexora.document_index import router as docs_router


def test_strict_tools_and_permission_separation():
    for row in fixtures():
        result = validate_call(row["expected"])
        assert not result["execution_authorized"]
    for call in [
        {"tool": "shell", "arguments": {"command": "whoami"}},
        {"tool": "read_file", "arguments": {"path": "../key"}},
        {"tool": "retry", "arguments": {"attempt": 2}},
        {"tool": "calculator", "arguments": {"expression": "1+2", "approved": True}},
        {"tool": "browse", "arguments": {"url": "https://127.0.0.1/"}},
    ]:
        with pytest.raises(ValueError):
            validate_call(call)


def test_tool_execution_keeps_privileged_calls_proposals(tmp_path):
    app = FastAPI()
    app.include_router(docs_router(tmp_path))
    app.include_router(tools_router(tmp_path))
    client = TestClient(app)
    result = client.post(
        "/api/tools/execute",
        json={"call": {"tool": "calculator", "arguments": {"expression": "17*23"}}},
    )
    assert result.status_code == 200 and result.json()["status"] == "executed"
    result = client.post(
        "/api/tools/execute",
        json={
            "call": {
                "tool": "create_file",
                "arguments": {"path": "new.txt", "content": "hello"},
            }
        },
    )
    assert (
        result.json()["status"] == "proposal_only"
        and not (tmp_path / "new.txt").exists()
    )


def setup(tmp_path, profile="python"):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "one.py").write_text("def f(x):return 0\n")
    (repo / "two.py").write_text("def g(x):return 0\n")
    ident = register(tmp_path, str(repo))["id"]
    return repo, create(
        tmp_path,
        Task(
            repository_id=ident,
            files=["one.py", "two.py"],
            goal="Fix f to return x and g to return x+1",
            acceptance="from pathlib import Path\nns={}\nexec(Path('one.py').read_text(),ns)\nexec(Path('two.py').read_text(),ns)\nassert ns['f'](3)==3 and ns['g'](3)==4",
            profile=profile,
        ),
    )


def test_multi_file_verified_apply_conflict_and_rollback(tmp_path):
    repo, task = setup(tmp_path)
    result = execute(
        tmp_path,
        task["id"],
        proposer=lambda *args: {
            "one.py": "def f(x):return x\n",
            "two.py": "def g(x):return x+1\n",
        },
    )
    assert result["status"] == "awaiting_approval", result.get("error")
    assert "return 0" in (repo / "one.py").read_text()
    with pytest.raises(ValueError):
        approve(tmp_path, task["id"], "0" * 64)
    approved = approve(tmp_path, task["id"], result["candidate_sha256"])
    assert approved["status"] == "completed"
    approved["status"] = "applying"
    save(tmp_path, approved)
    rollback(tmp_path, approved)
    assert (
        "return 0" in (repo / "one.py").read_text()
        and "return 0" in (repo / "two.py").read_text()
    )


def test_scope_and_cancel_prevent_edits(tmp_path):
    repo, task = setup(tmp_path)
    result = execute(
        tmp_path, task["id"], proposer=lambda *args: {"../outside.py": "bad"}
    )
    assert result["status"] == "failed" and "return 0" in (repo / "one.py").read_text()
    assert not (tmp_path / "outside.py").exists()


def test_node_typescript_control_isolated(tmp_path):
    from nexora.language_sandbox import run

    (tmp_path / "solution.ts").write_text(
        "export function fn(x:number):number{return x*2;}"
    )
    test = "const fs=require('fs'),vm=require('vm'),ts=require('/opt/typescript/typescript.js');const c={exports:{}};vm.runInNewContext(ts.transpileModule(fs.readFileSync('solution.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,c);if(c.exports.fn(3)!==6)throw Error('bad');console.log('OK');"
    result = run(tmp_path, "typescript", test)
    assert result.startswith("Exit code: 0\n") and "OK" in result
    assert run(tmp_path, "php", "x").startswith("BLOCKED:")


def test_document_database_migration_and_conflicting_dates(tmp_path):
    from nexora.document_index import (
        connection,
        initialize,
        ingest,
        Document,
        field_evidence,
    )

    with connection(tmp_path) as con:
        con.execute(
            "CREATE TABLE documents(id TEXT PRIMARY KEY,project TEXT,title TEXT,source TEXT,digest TEXT,created REAL,UNIQUE(project,digest))"
        )
    initialize(tmp_path)
    ingest(
        tmp_path,
        Document(
            title="Old",
            text="stock: 2",
            source="urn:test:old",
            published_at="2020-01-01",
        ),
    )
    assert (
        field_evidence(tmp_path, "local", ["stock"], "2026-01-01")["status"]
        == "insufficient_evidence"
    )
    ingest(
        tmp_path,
        Document(
            title="New",
            text="stock: 12",
            source="urn:test:new",
            published_at="2026-10-19",
        ),
    )
    assert (
        field_evidence(tmp_path, "local", ["stock"], "2026-01-01")["fields"]["stock"][
            "answer"
        ]
        == "12"
    )
    ingest(
        tmp_path,
        Document(
            title="Conflict",
            text="stock: 99",
            source="urn:test:conflict",
            published_at="2026-10-19",
        ),
    )
    assert (
        field_evidence(tmp_path, "local", ["stock"], "2026-01-01")["status"]
        == "conflicting_sources"
    )


@pytest.mark.parametrize("provider", ["qwen-coder", "ollama"])
def test_streamed_qwen_turn_persists_final_answer(tmp_path, monkeypatch, provider):
    from nexora.cowork import router
    import nexora.assistant_backend

    def fake(model, messages, max_tokens, stream_callback=None):
        if stream_callback:
            stream_callback("Hello")
            stream_callback(" world")
        return {"text": "Hello world"}

    monkeypatch.setattr(nexora.assistant_backend, "generate", fake)
    app = FastAPI()
    app.include_router(router(tmp_path, lambda _: {}))
    client = TestClient(app)
    ident = client.post("/api/cowork/threads").json()["id"]
    result = client.post(
        "/api/cowork/threads/" + ident + "/messages/stream",
        json={"provider": provider, "text": "hello"},
    )
    assert (
        result.status_code == 200
        and '"type": "delta"' in result.text
        and '"type": "result"' in result.text
    )
    messages = client.get("/api/cowork/threads/" + ident).json()
    assert (
        messages[-1]["text"] == "Hello world" and "external" in messages[-1]["provider"]
    )


def test_missing_workspace_tasks_and_current_unknown_date(tmp_path):
    from nexora.workspace_code import router
    from nexora.document_index import initialize, ingest, Document, field_evidence

    app = FastAPI()
    app.include_router(router(tmp_path))
    client = TestClient(app)
    assert client.post("/api/workspace-code/tasks/missing/cancel").status_code == 404
    assert client.get("/api/workspace-code/tasks/missing").status_code == 404
    initialize(tmp_path)
    ingest(
        tmp_path,
        Document(title="Unknown date", text="stock: 12", source="urn:test:unknown"),
    )
    assert (
        field_evidence(tmp_path, "local", ["stock"], "2026-01-01")["status"]
        == "insufficient_evidence"
    )


def test_local_backend_rejects_incomplete_stream_and_releases_gate(monkeypatch):
    import httpx
    from fastapi import HTTPException
    from nexora import assistant_backend, reference

    original = httpx.Client
    bad = [True]

    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"name": reference.MODEL, "digest": reference.MODEL_DIGEST}
                    ]
                },
            )
        content = (
            '{"message":{"content":"Hi"},"done":false}\n'
            if bad[0]
            else '{"message":{"content":"Hi"},"done":true,"eval_count":1,"eval_duration":0}\n'
        )
        return httpx.Response(200, content=content)

    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    with pytest.raises(HTTPException):
        assistant_backend.generate("smollm2", [{"role": "user", "content": "hello"}], 8)
    bad[0] = False
    result = assistant_backend.generate(
        "smollm2", [{"role": "user", "content": "hello"}], 8
    )
    assert result["text"] == "Hi" and result["tokens_per_second"] is None
    assert not reference._lock.locked()


def test_multi_file_apply_preserves_concurrent_owner_edit(tmp_path, monkeypatch):
    import os

    repo, task = setup(tmp_path)
    result = execute(
        tmp_path,
        task["id"],
        proposer=lambda *args: {
            "one.py": "def f(x):return x\n",
            "two.py": "def g(x):return x+1\n",
        },
    )
    assert result["status"] == "awaiting_approval"
    original = os.replace
    fired = []

    def replace(src, dst):
        original(src, dst)
        if str(dst) == str(repo / "one.py") and not fired:
            fired.append(True)
            (repo / "two.py").write_text("owner concurrent edit\n")

    monkeypatch.setattr(os, "replace", replace)
    with pytest.raises(ValueError, match="Source changed"):
        approve(tmp_path, task["id"], result["candidate_sha256"])
    assert (repo / "one.py").read_text() == "def f(x):return 0\n"
    assert (repo / "two.py").read_text() == "owner concurrent edit\n"
