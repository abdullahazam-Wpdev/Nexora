import json
import subprocess
import types
import numpy as np
import pytest
import torch
from nexora.artifacts import atomic_json
from nexora.expansion import freeze_suite, publish_expansion
from nexora.research import (
    Core,
    Config,
    TrainConfig,
    Monitor,
    evaluate,
    create_run,
    train_run,
    migrate_v2_run,
    verify_checkpoint,
)
from test_research import fixture_dataset, config


def record(source, text):
    import hashlib

    return {
        "source_id": source,
        "text": text,
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


def test_frozen_holdouts_survive_expansion_and_remove_contamination(tmp_path):
    v = [record("v", " ".join(f"validationWord{i}" for i in range(50)))]
    t = [record("t", " ".join(f"testWord{i}" for i in range(50)))]
    suite = freeze_suite(
        "fixed",
        v,
        t,
        notices={"license": "retained"},
        sources={"v": "a", "t": "b"},
        store=tmp_path,
    )
    clean = record("train", " ".join(f"trainingWord{i}" for i in range(50)))
    dirty = record("other", v[0]["text"] + " copied extension")
    first = publish_expansion(
        "base",
        [clean, dirty],
        suite,
        notices={"license": "retained"},
        provenance="test fixtures",
        reviewer="test",
        store=tmp_path,
    )
    extra = record("new", " ".join(f"newWord{i}" for i in range(50)))
    second = publish_expansion(
        "more",
        [clean, dirty, extra],
        suite,
        notices={"license": "retained"},
        provenance="test fixtures",
        reviewer="test",
        store=tmp_path,
    )
    assert first["files"]["validation.jsonl"] == second["files"]["validation.jsonl"]
    assert first["files"]["test.jsonl"] == second["files"]["test.jsonl"]
    assert second["quality"]["rejected"]["heldout_contamination"] == 1
    assert second["quality"]["accepted_train_documents"] == 2
    with pytest.raises(ValueError, match="cannot be changed"):
        freeze_suite(
            "fixed",
            v,
            [record("t", "changed")],
            notices={"license": "retained"},
            sources={"v": "a", "t": "b"},
            store=tmp_path,
        )


def test_batched_evaluation_equivalent_and_preserves_rng():
    torch.set_num_threads(2)
    torch.manual_seed(5)
    m = Core(Config(vocab_size=32, dim=32, layers=2, heads=4, context=16))
    tokens = np.arange(159) % 32
    state = torch.get_rng_state().clone()
    a = evaluate(m, tokens, 16, batch_size=1)
    b = evaluate(m, tokens, 16, batch_size=8)
    assert a["tokens"] == b["tokens"] == 158
    assert abs(a["loss"] - b["loss"]) < 1e-6
    assert torch.equal(state, torch.get_rng_state())


def test_sensor_sampling_keeps_cancellation_immediate(tmp_path, monkeypatch):
    from nexora import research

    reads = []
    monkeypatch.setattr(research, "temperature", lambda: reads.append(1) or 45)
    c = TrainConfig(max_rss_mb=1600, min_available_mb=256, temperature_interval=2)
    m = Monitor(c, tmp_path, tmp_path / "cancel")
    m.check()
    m.check()
    assert len(reads) == 1
    (tmp_path / "cancel").write_text("stop")
    with pytest.raises(RuntimeError, match="Cancellation requested"):
        m.check()


def test_architecture_is_validated_and_controls_actual_model(tmp_path):
    for arch in ({"dim": 999}, {"dim": 256, "layers": 6, "heads": 8, "context": 128}):
        with pytest.raises(ValueError):
            TrainConfig(architecture=arch)
    data = fixture_dataset(tmp_path)
    options = {
        **config(2),
        "architecture": {"dim": 48, "layers": 2, "heads": 4, "context": 32},
        "evaluate_test": False,
    }
    run = create_run(data["id"], training=options, run_id="custom", store=tmp_path)
    result = train_run(run["id"], store=tmp_path)
    assert result["config"]["dim"] == 48 and result["config"]["context"] == 32
    assert result["test"] is None


def test_version2_migration_preserves_next_update_exactly(tmp_path):
    # Execute the actual committed v2 trainer against isolated numerical fixtures.
    text = subprocess.check_output(
        ["git", "show", "72ea4d7:nexora/research.py"], text=True
    )
    module = types.ModuleType("nexora._committed_phase2")
    import sys

    sys.modules[module.__name__] = module
    exec(compile(text, "72ea4d7:nexora/research.py", "exec"), module.__dict__)
    module.code_identity = lambda: "verified-committed-v2-test"
    data = fixture_dataset(tmp_path)
    module.create_run(data["id"], training=config(3), run_id="v2-whole", store=tmp_path)
    module.train_run("v2-whole", store=tmp_path)
    module.create_run(
        data["id"], training=config(3), run_id="v2-parent", store=tmp_path
    )
    module.train_run("v2-parent", additional_steps=2, store=tmp_path)
    migrate_v2_run("v2-parent", "v3-fork", store=tmp_path)
    train_run("v3-fork", resume=True, additional_steps=1, store=tmp_path)
    a, ap = verify_checkpoint(tmp_path / "runs/v2-whole")
    b, bp = verify_checkpoint(tmp_path / "runs/v3-fork")
    sa = torch.load(ap / "resume.pt", weights_only=True)
    sb = torch.load(bp / "resume.pt", weights_only=True)
    assert a["step"] == b["step"] == 3
    for k in sa["model"]:
        torch.testing.assert_close(sa["model"][k], sb["model"][k], rtol=0, atol=0)
    assert torch.equal(sa["sampler_rng"], sb["sampler_rng"])
    assert (
        json.loads((tmp_path / "runs/v2-parent/result.json").read_text())[
            "engine_version"
        ]
        == 2
    )


def test_fractional_dimensions_and_budgets_are_rejected():
    for value in (
        {"batch_size": 2.5},
        {"seed": True},
        {"steps": 5.5},
        {"min_battery_percent": -1},
    ):
        with pytest.raises(ValueError):
            TrainConfig(**value)


def test_generation_diagnostics_do_not_equate_overlap_with_ability():
    from nexora.generation_eval import diagnostics

    r = diagnostics("echo echo echo echo echo echo", "echo echo echo echo echo echo")
    assert r["distinct_1"] == 1 / 6
    assert r["repeated_trigram_fraction"] > 0
    assert r["longest_exact_training_word_span_capped_32"] == 6
    assert "instruction_following" not in r


def test_stale_version_resume_is_rejected_before_launch(tmp_path):
    from nexora import jobs

    folder = tmp_path / "runs/legacy"
    folder.mkdir(parents=True)
    atomic_json(
        folder / "result.json",
        {"id": "legacy", "engine_version": 2, "status": "completed", "started_at": 1},
    )
    atomic_json(folder / "latest.json", {"step": 1})
    with pytest.raises(ValueError, match="migration"):
        jobs.launch(tmp_path, "legacy", resume=True)


def test_version3_checkpoint_fork_preserves_state_and_parent(tmp_path):
    from nexora.research import fork_checkpoint

    data = fixture_dataset(tmp_path)
    create_run(data["id"], training=config(4), run_id="reference", store=tmp_path)
    train_run("reference", store=tmp_path)
    create_run(data["id"], training=config(4), run_id="parent3", store=tmp_path)
    train_run("parent3", additional_steps=2, store=tmp_path)
    parent_bytes = (tmp_path / "runs/parent3/result.json").read_bytes()
    fork_checkpoint("parent3", "fork3", store=tmp_path)
    train_run("fork3", resume=True, additional_steps=2, store=tmp_path)
    _, a = verify_checkpoint(tmp_path / "runs/reference")
    _, b = verify_checkpoint(tmp_path / "runs/fork3")
    sa = torch.load(a / "resume.pt", weights_only=True)
    sb = torch.load(b / "resume.pt", weights_only=True)
    for key in sa["model"]:
        torch.testing.assert_close(sa["model"][key], sb["model"][key], atol=0, rtol=0)
    assert (tmp_path / "runs/parent3/result.json").read_bytes() == parent_bytes


def test_persistent_matrix_deadline_cannot_be_renewed_by_retry(tmp_path, monkeypatch):
    from nexora import scaling_experiments as framework

    plan = {"runs": [], "max_matrix_seconds": 240}
    atomic_json(tmp_path / "phase3-plan.json", plan)
    ledger = {
        "plan_sha256": framework.plan_fingerprint(plan),
        "deadline_epoch": 90,
        "state": "running",
    }
    atomic_json(tmp_path / "phase3-execution.json", ledger)
    monkeypatch.setattr(framework, "STORE", tmp_path)
    monkeypatch.setattr(framework.time, "time", lambda: 100)
    with pytest.raises(RuntimeError, match="Persistent matrix deadline"):
        framework.execute_plan()
    assert (
        json.loads((tmp_path / "phase3-execution.json").read_text())["deadline_epoch"]
        == 90
    )
