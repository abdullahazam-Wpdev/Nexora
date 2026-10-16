import json
import numpy as np
import pytest
import torch
from nexora.artifacts import identifier, lock
from nexora.data_engine import build_dataset, load_dataset
from nexora.research import (
    TrainConfig,
    create_run,
    train_run,
    verify_checkpoint,
    evaluate,
    infer_run,
    Monitor,
    BudgetExceeded,
    learning_rate,
)
from nexora.model import Core, Config


def fixture_dataset(tmp_path):
    # Deterministic numerical fixtures, not proprietary model-generated prose.
    docs = [
        {
            "source_id": f"group-{i}",
            "text": " ".join(
                f"Group{chr(65 + i)}number{j} equals {i + j}." for j in range(20)
            ),
        }
        for i in range(12)
    ]
    return build_dataset(
        "fixture",
        docs,
        approved=True,
        license="CC0-1.0",
        provenance="Deterministic local numeric test fixture",
        store=tmp_path,
    )


def test_dataset_source_holdout_and_integrity(tmp_path):
    manifest = fixture_dataset(tmp_path)
    m, splits = load_dataset(manifest["id"], tmp_path)
    groups = [{d["source_id"] for d in docs} for docs in splits.values()]
    assert not (groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2])
    assert manifest["id"] == fixture_dataset(tmp_path)["id"]
    with (tmp_path / "datasets" / manifest["id"] / "test.jsonl").open("a") as f:
        f.write("tamper")
    with pytest.raises(ValueError, match="integrity"):
        load_dataset(manifest["id"], tmp_path)


def test_strict_config_and_paths():
    for x in ("../secrets", "/tmp/model", "a/b", ""):
        with pytest.raises(ValueError):
            identifier(x)
    for options in (
        {"steps": 0},
        {"batch_size": 999},
        {"max_seconds": 9999},
        {"min_available_mb": 0},
    ):
        with pytest.raises(ValueError):
            TrainConfig(**options)
    assert learning_rate(0, TrainConfig()) < learning_rate(20, TrainConfig())
    assert learning_rate(1000, TrainConfig()) < learning_rate(20, TrainConfig())


def test_evaluation_counts_remainder_and_does_not_consume_rng():
    torch.set_num_threads(2)
    m = Core(Config(vocab_size=20, dim=16, heads=2, layers=1, context=8))
    tokens = np.arange(19) % 20
    state = torch.get_rng_state().clone()
    result = evaluate(m, tokens, 8)
    assert result["tokens"] == 18 and result["perplexity"] > 0
    assert torch.equal(state, torch.get_rng_state())
    assert m.training


def config(steps):
    return {
        "steps": steps,
        "batch_size": 2,
        "accumulation": 1,
        "eval_every": 2,
        "checkpoint_every": 2,
        "vocab_size": 300,
        "max_rss_mb": 1600,
        "min_available_mb": 256,
    }


def test_exact_resume_matches_uninterrupted_and_rejects_corruption(tmp_path):
    dataset = fixture_dataset(tmp_path)
    create_run(dataset["id"], training=config(4), run_id="whole", store=tmp_path)
    whole = train_run("whole", store=tmp_path)
    create_run(dataset["id"], training=config(4), run_id="split", store=tmp_path)
    train_run("split", additional_steps=2, store=tmp_path)
    resumed = train_run("split", resume=True, additional_steps=2, store=tmp_path)
    a, ap = verify_checkpoint(tmp_path / "runs/whole")
    b, bp = verify_checkpoint(tmp_path / "runs/split")
    sa = torch.load(ap / "resume.pt", weights_only=True)
    sb = torch.load(bp / "resume.pt", weights_only=True)
    assert a["step"] == b["step"] == 4
    for key in sa["model"]:
        torch.testing.assert_close(sa["model"][key], sb["model"][key], rtol=0, atol=0)
    assert torch.equal(sa["sampler_rng"], sb["sampler_rng"])
    assert sa["scheduler"] == sb["scheduler"]
    assert sa["optimizer"]["param_groups"] == sb["optimizer"]["param_groups"]
    for param, state in sa["optimizer"]["state"].items():
        for key, value in state.items():
            torch.testing.assert_close(
                value, sb["optimizer"]["state"][param][key], rtol=0, atol=0
            )
    for step_a, step_b in zip(whole["history"], resumed["history"]):
        assert (
            step_a["train_loss"] == step_b["train_loss"]
            and step_a["lr"] == step_b["lr"]
        )
    assert whole["validation"] == resumed["validation"]
    assert infer_run("split", "Number", 4, store=tmp_path)["new_tokens"] == 4
    with pytest.raises(ValueError, match="immutable"):
        train_run("whole", store=tmp_path)
    with (bp / "model.safetensors").open("ab") as f:
        f.write(b"tamper")
    with pytest.raises(ValueError, match="integrity"):
        verify_checkpoint(tmp_path / "runs/split")


def test_budget_stop_is_durable(tmp_path, monkeypatch):
    dataset = fixture_dataset(tmp_path)
    create_run(dataset["id"], training=config(2), run_id="budget", store=tmp_path)
    monkeypatch.setattr(
        Monitor,
        "check",
        lambda self: (_ for _ in ()).throw(BudgetExceeded("test budget")),
    )
    with pytest.raises(BudgetExceeded):
        train_run("budget", store=tmp_path)
    result = json.loads((tmp_path / "runs/budget/result.json").read_text())
    assert result["status"] == "stopped" and "test budget" in result["error"]


def test_cli_and_api_share_training_lock(tmp_path):
    dataset = fixture_dataset(tmp_path)
    create_run(dataset["id"], training=config(2), run_id="lock-test", store=tmp_path)
    with lock(tmp_path / ".training.lock"):
        with pytest.raises(ValueError, match="lock"):
            train_run("lock-test", store=tmp_path)


def test_resume_launch_window_counts_as_active(tmp_path, monkeypatch):
    from nexora import jobs
    from nexora.artifacts import atomic_json

    folder = tmp_path / "runs" / "resume-window"
    folder.mkdir(parents=True)
    atomic_json(
        folder / "result.json",
        {"id": "resume-window", "status": "completed", "started_at": 1},
    )
    atomic_json(folder / "launch.json", {"pid": 123, "process_started": 2})
    monkeypatch.setattr(jobs, "alive", lambda pid, created: pid == 123)
    result = jobs.status(tmp_path, "resume-window")
    assert result["running"] and result["status"] == "queued"
    assert len(jobs.active_runs(tmp_path)) == 1
