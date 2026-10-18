import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from nexora.agent_runtime import (
    CodingTask,
    register,
    create,
    execute,
    approve,
    check_python,
    router,
    folder,
)
from nexora.project_memory import router as memory_router
from nexora.openai_nim_models import router as models_router


def setup(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def add(a,b):\n return a-b\n")
    ident = register(tmp_path, str(repo))["id"]
    body = CodingTask(
        repository_id=ident,
        path="app.py",
        goal="Add two numbers",
        acceptance="assert add(2,3)==5",
        proposed_code="def add(a,b):\n return a+b\n",
    )
    return repo, body


def pass_runner(stage, target):
    # Unit fixture only. Separate live benchmark uses actual Podman execution.
    import re

    marker = re.search(r"VERIFIED_[a-f0-9]+", target.read_text()).group()
    return "Exit code: 0\n" + marker


def test_approval_and_optimistic_integrity(tmp_path):
    repo, body = setup(tmp_path)
    task = create(tmp_path, body)
    out = execute(tmp_path, task["id"], runner=pass_runner)
    assert out["status"] == "awaiting_approval"
    assert "a-b" in (repo / "app.py").read_text()
    with pytest.raises(ValueError):
        approve(tmp_path, task["id"], "wrong")
    approve(tmp_path, task["id"], out["candidate_sha256"])
    assert "a+b" in (repo / "app.py").read_text()
    with pytest.raises(ValueError):
        approve(tmp_path, task["id"], out["candidate_sha256"])


def test_changed_source_rejected(tmp_path):
    repo, body = setup(tmp_path)
    task = create(tmp_path, body)
    out = execute(tmp_path, task["id"], runner=pass_runner)
    (repo / "app.py").write_text("owner changed this")
    with pytest.raises(ValueError):
        approve(tmp_path, task["id"], out["candidate_sha256"])
    assert (repo / "app.py").read_text() == "owner changed this"


def test_no_unsafe_import_or_traversal(tmp_path):
    repo, body = setup(tmp_path)
    for code in ["import os", 'eval("1")', "x.__class__", "import socket"]:
        with pytest.raises(ValueError):
            check_python(code)
    body.path = "../outside.py"
    with pytest.raises(ValueError):
        create(tmp_path, body)
    (repo / "link.py").symlink_to(tmp_path / "outside.py")
    body.path = "link.py"
    with pytest.raises(ValueError):
        create(tmp_path, body)


def test_cancel_after_proposal_and_bounded_retries(tmp_path):
    repo, body = setup(tmp_path)
    body.proposed_code = None
    task = create(tmp_path, body)

    def proposal(*args):
        (folder(tmp_path, task["id"]) / "cancel").touch()
        return "def add(a,b):return a+b"

    out = execute(tmp_path, task["id"], proposer=proposal, runner=pass_runner)
    assert out["status"] == "cancelled" and "a-b" in (repo / "app.py").read_text()
    task = create(tmp_path, body)
    out = execute(tmp_path, task["id"], proposer=lambda *a: "not python at all")
    assert out["status"] == "failed" and out["attempts"] == 2


def test_interrupted_worker_detected_and_persistent(tmp_path):
    _, body = setup(tmp_path)
    task = create(tmp_path, body)
    p = folder(tmp_path, task["id"]) / "task.json"
    task.update(status="running", pid=99999999, process_created=0)
    p.write_text(json.dumps(task))
    app = FastAPI()
    app.include_router(router(tmp_path))
    c = TestClient(app)
    assert c.get("/api/agent/tasks/" + task["id"]).json()["status"] == "interrupted"
    app2 = FastAPI()
    app2.include_router(router(tmp_path))
    assert (
        TestClient(app2).get("/api/agent/tasks/" + task["id"]).json()["status"]
        == "interrupted"
    )


def test_memory_correction_deletion_and_boundaries(tmp_path):
    app = FastAPI()
    app.include_router(memory_router(tmp_path))
    c = TestClient(app)
    body = {
        "kind": "project",
        "content": "Use Python",
        "provenance": "owner",
        "project": "one",
    }
    row = c.post("/api/knowledge/entries", json=body).json()
    ident = row["id"]
    assert c.post("/api/knowledge/entries", json=body).json()["id"] == ident
    assert not c.get("/api/knowledge/entries?project=two").json()["entries"]
    assert row["training_approved"] is False and row["permission_authority"] is False
    body["content"] = "Use typed Python"
    assert c.put("/api/knowledge/entries/" + ident, json=body).status_code == 200
    assert c.get("/api/knowledge/entries?project=one&q=typed").json()["entries"]
    c.delete("/api/knowledge/entries/" + ident)
    assert not c.get("/api/knowledge/entries?project=one").json()["entries"]


def test_whisper_is_not_a_chat_model(tmp_path, monkeypatch):
    app = FastAPI()
    app.include_router(models_router())
    c = TestClient(app)
    monkeypatch.delenv("NEXORA_WHISPER_BASE", raising=False)
    models = c.get("/api/nvidia/openai-models").json()["models"]
    assert models[0]["chat"] is True and models[1]["chat"] is False
    assert (
        c.post("/api/speech/transcribe", json={"wav_base64": "abcd"}).status_code == 503
    )


def test_completion_only_mask_and_no_dataset_overlap():
    from nexora.tool_sft import dataset, encode_example
    from tokenizers import Tokenizer, models, trainers, pre_tokenizers

    t = Tokenizer(models.BPE(unk_token="[UNK]"))
    t.pre_tokenizer = pre_tokenizers.ByteLevel()
    d = dataset()
    t.train_from_iterator(
        [r["prompt"] + r["response"] for r in d["train"]],
        trainers.BpeTrainer(
            vocab_size=512,
            special_tokens=["[UNK]", "[RESPONSE]", "[EOS]"],
            initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
        ),
    )
    x, y = encode_example(t, d["train"][0], 128)
    prefix = len(t.encode(d["train"][0]["prompt"]).ids) + 1
    assert (y[: prefix - 1] == -100).all() and y[prefix - 1] != -100
    assert (y == -100).any() and (y != -100).any()
    assert not ({r["id"] for r in d["train"]} & {r["id"] for r in d["test"]})


def test_recorded_apply_recovery_and_no_unapproved_edit(tmp_path):
    repo, body = setup(tmp_path)
    task = create(tmp_path, body)
    out = execute(tmp_path, task["id"], runner=pass_runner)
    p = folder(tmp_path, task["id"]) / "task.json"
    out["status"] = "applying"
    p.write_text(json.dumps(out))
    (repo / "app.py").write_text(body.proposed_code)
    app = FastAPI()
    app.include_router(router(tmp_path))
    c = TestClient(app)
    recovered = c.get("/api/agent/tasks/" + task["id"]).json()
    assert recovered["status"] == "completed"
    assert recovered["events"][-1]["action"] == "recover_recorded_apply"


def test_calculation_budget_and_no_execution():
    from nexora.verification import calculate

    assert calculate("17 * 23") == 391
    for expression in [
        '__import__("os")',
        "2**100000",
        'float("inf")',
        "(1).__class__",
    ]:
        with pytest.raises(ValueError):
            calculate(expression)


def test_literal_claim_requires_stored_citation(tmp_path):
    from nexora.verification import router as verification_router

    (tmp_path / "research-evidence").mkdir()
    (tmp_path / "research-evidence/source.json").write_text(
        json.dumps(
            {
                "citations": [
                    {
                        "citation_id": "c1",
                        "url": "https://example.com",
                        "full_text_excerpt": "Exact supported excerpt.",
                    }
                ]
            }
        )
    )
    app = FastAPI()
    app.include_router(verification_router(tmp_path))
    c = TestClient(app)
    assert (
        c.post(
            "/api/verification/claim",
            json={
                "text": "Exact supported excerpt.",
                "evidence_id": "source",
                "citation_id": "c1",
            },
        ).json()["supported"]
        is True
    )
    assert (
        c.post(
            "/api/verification/claim",
            json={
                "text": "Invented fact",
                "evidence_id": "source",
                "citation_id": "c1",
            },
        ).json()["claim_kind"]
        == "unverified"
    )


def test_registered_source_inventory_and_missing_path(tmp_path):
    repo, body = setup(tmp_path)
    with pytest.raises(ValueError):
        register(tmp_path, "")
    (repo / ".env").write_text("never display")
    app = FastAPI()
    app.include_router(router(tmp_path))
    c = TestClient(app)
    rows = c.get("/api/agent/repositories/" + body.repository_id + "/files").json()[
        "files"
    ]
    assert [r["path"] for r in rows] == ["app.py"]
    result = c.get(
        "/api/agent/repositories/" + body.repository_id + "/source",
        params={"path": "app.py"},
    ).json()
    assert result["python_symbols"] == ["add"]
    assert (
        c.get(
            "/api/agent/repositories/" + body.repository_id + "/source",
            params={"path": "../private.py"},
        ).status_code
        == 409
    )


def test_hosted_chat_requires_explicit_consent(tmp_path, monkeypatch):
    from nexora.cowork import router as cowork_router
    from nexora import nvidia_nim

    def forbidden(*args, **kwargs):
        raise AssertionError("No hosted request without consent")

    monkeypatch.setattr(nvidia_nim, "request", forbidden)
    app = FastAPI()
    app.include_router(cowork_router(tmp_path, lambda _: {}))
    c = TestClient(app)
    ident = c.post("/api/cowork/threads").json()["id"]
    result = c.post(
        f"/api/cowork/threads/{ident}/messages",
        json={"provider": "nvidia-gpt-oss-20b", "text": "hello"},
    ).json()
    assert result["role"] == "error" and "consent" in result["text"]
