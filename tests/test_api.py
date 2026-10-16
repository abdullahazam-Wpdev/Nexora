import importlib
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    import nexora.config as config

    monkeypatch.setattr(config, "STORE", tmp_path)
    import nexora.api as api

    importlib.reload(api)
    return TestClient(api.app)


def test_health_projects_and_memory(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/projects").json()[0]["id"] == "local"
    assert (
        client.post(
            "/api/memory",
            json={"content": "Reproduce experiments before promoting checkpoints."},
        ).status_code
        == 201
    )
    assert len(client.get("/api/memory").json()) == 1
    assert client.get("/api/audit").json()[0]["action"] == "memory.create"


def test_origin_and_inference_guards(client):
    assert (
        client.post(
            "/api/memory",
            headers={"Origin": "https://untrusted.example"},
            json={"content": "bad"},
        ).status_code
        == 403
    )
    assert client.post("/api/generate", json={"prompt": "hello"}).status_code == 409
    assert (
        client.post(
            "/api/generate", json={"prompt": "hello", "max_tokens": 10000}
        ).status_code
        == 422
    )
    assert client.post("/api/training", json={"resume": True}).status_code == 409


def test_dataset_ingestion(client):
    body = {
        "name": "fixture",
        "texts": [f"Unique local numerical fixture document {i}." for i in range(20)],
        "license": "CC0-1.0",
        "provenance": "test-owned numerical fixtures",
        "approved": False,
    }
    assert client.post("/api/datasets", json=body).status_code == 422
    body["approved"] = True
    assert client.post("/api/datasets", json=body).status_code == 201
    assert client.post("/api/datasets", json=body).status_code == 409
    assert client.get("/api/datasets").json()[0]["documents"] == 20


def test_research_api_approval_runs_and_hosts(client):
    assert (
        client.get("/api/health", headers={"Host": "attacker.invalid"}).status_code
        == 400
    )
    body = {
        "name": "api-data",
        "documents": [
            {
                "source_id": f"source-{i}",
                "text": " ".join(
                    f"Group{chr(65 + i)}number{j} equals {i + j}." for j in range(20)
                ),
            }
            for i in range(10)
        ],
        "approved": True,
        "license": "CC0-1.0",
        "provenance": "Numerical fixture generated in test",
        "reviewer": "local-owner",
    }
    ingested = client.post("/api/research/datasets", json=body)
    assert ingested.status_code == 201, ingested.text
    dataset_id = ingested.json()["id"]
    request = {
        "dataset_id": dataset_id,
        "profile": "tiny",
        "training": {"steps": 2},
        "start": False,
    }
    run = client.post("/api/research/runs", json=request)
    assert run.status_code == 202, run.text
    run_id = run.json()["id"]
    assert client.get("/api/research/runs/" + run_id).json()["status"] == "queued"
    assert client.get("/api/research/datasets/" + dataset_id).json()["approved"]
    assert client.post("/api/research/runs/" + run_id + "/select").status_code == 404
    assert (
        client.post(
            "/api/research/runs", json={**request, "training": {"max_seconds": 999999}}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/research/runs", json={**request, "profile": "large"}
        ).status_code
        == 422
    )
