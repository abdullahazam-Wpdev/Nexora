import json
import pytest
from fastapi import HTTPException
from nexora.minimal_patch import apply_edits
from nexora.compute_budget import admission
from nexora.answer_verification import verify_claims, ranked_sources
from test_phase9 import setup
from nexora.workspace_code import execute, approve, read


def test_unique_minimal_edits_and_scope():
    original = {"a.py": "# keep\nx=1\n"}
    assert apply_edits(
        original, {"edits": [{"path": "a.py", "old": "x=1", "new": "x=2"}]}
    ) == {"a.py": "# keep\nx=2\n"}
    for e in [
        {"path": "../b", "old": "x=1", "new": "x=2"},
        {"path": "a.py", "old": "missing", "new": "x=2"},
        {"path": "a.py", "old": "", "new": "x=2"},
    ]:
        with pytest.raises(ValueError):
            apply_edits(original, {"edits": [e]})
    with pytest.raises(ValueError):
        apply_edits({"a": "xx"}, {"edits": [{"path": "a", "old": "x", "new": "y"}]})


def test_cross_process_compute_exclusion(tmp_path):
    import subprocess, sys

    with admission("training", tmp_path):
        with pytest.raises(HTTPException) as err:
            with admission("inference", tmp_path):
                pass
        assert err.value.status_code == 429
        code = (
            'from pathlib import Path;from nexora.compute_budget import admission;from fastapi import HTTPException\ntry:\n with admission("inference",Path('
            + repr(str(tmp_path))
            + ')):raise RuntimeError("overlap")\nexcept HTTPException as e: assert e.status_code==429'
        )
        subprocess.run([sys.executable, "-c", code], check=True, timeout=10)
    with admission("inference", tmp_path):
        pass


def test_minimal_patch_runs_real_sandbox_and_post_apply(tmp_path):
    repo, t = setup(tmp_path)
    t["request"]["patch_format"] = "edits"
    from nexora.workspace_code import save

    save(tmp_path, t)
    r = execute(
        tmp_path,
        t["id"],
        proposer=lambda *args: {
            "edits": [
                {"path": "one.py", "old": "return 0", "new": "return x"},
                {"path": "two.py", "old": "return 0", "new": "return x+1"},
            ]
        },
    )
    assert r["status"] == "awaiting_approval"
    result = approve(tmp_path, t["id"], r["candidate_sha256"])
    assert (
        result["status"] == "completed" and result["post_apply_verification"]["passed"]
    )


def test_failed_applied_tree_rolls_back(tmp_path, monkeypatch):
    import nexora.workspace_code as w

    repo, t = setup(tmp_path)
    r = execute(
        tmp_path,
        t["id"],
        proposer=lambda *args: {
            "one.py": "def f(x):return x\n",
            "two.py": "def g(x):return x+1\n",
        },
    )
    monkeypatch.setattr(w, "run", lambda *a: "Exit code: 1\nfailed")
    with pytest.raises(ValueError, match="Applied-tree"):
        approve(tmp_path, t["id"], r["candidate_sha256"])
    assert "return 0" in (repo / "one.py").read_text()
    assert read(tmp_path, t["id"])["status"] == "interrupted"


def test_frozen_suite_hashes():
    from pathlib import Path
    import hashlib

    root = Path("benchmarks/phase10")
    manifest = json.loads((root / "freeze.json").read_text())
    for name, expected in manifest["files"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected
    assert len(json.loads((root / "tasks.json").read_text())["tasks"]) >= 30


def test_claims_reject_missing_fabricated_and_tampered():
    import hashlib

    c = {
        "citation_id": "c1",
        "url": "https://example.org",
        "full_text_excerpt": "Limit is 5.",
        "content_hash": hashlib.sha256(b"https://example.orgLimit is 5.").hexdigest(),
    }
    r = verify_claims(
        [
            {"citation_id": "c1", "text": "Limit is 5."},
            {"citation_id": "c1", "text": "Limit is 50."},
            {"citation_id": "missing", "text": "Limit is 5."},
        ],
        [c],
    )
    assert (r["supported"], r["unsupported"]) == (1, 2)
    c["full_text_excerpt"] = "Limit is 50."
    assert (
        verify_claims([{"citation_id": "c1", "text": "Limit is 50."}], [c])[
            "unsupported"
        ]
        == 1
    )


def test_research_canonical_dedupe_and_relevance():
    rows = [
        {
            "url": "https://example.org/a?utm_source=x",
            "title": "unrelated",
            "snippet": "",
        },
        {"url": "https://example.org/a", "title": "duplicate", "snippet": ""},
        {
            "url": "https://example.org/b",
            "title": "Python API errors",
            "snippet": "Python",
        },
    ]
    out = ranked_sources("Python API", rows)
    assert len(out) == 2 and out[0]["url"].endswith("/b")


def test_stale_approval_cancel_and_interruption(tmp_path):
    from nexora.workspace_code import folder, save, rollback

    repo, t = setup(tmp_path)
    result = execute(
        tmp_path,
        t["id"],
        proposer=lambda *a: {
            "one.py": "def f(x):return x\n",
            "two.py": "def g(x):return x+1\n",
        },
    )
    (repo / "one.py").write_text("# owner edit\n")
    with pytest.raises(ValueError, match="Original sources"):
        approve(tmp_path, t["id"], result["candidate_sha256"])
    assert (repo / "one.py").read_text() == "# owner edit\n"
    # Cancellation is checked before touching any original.
    (folder(tmp_path, t["id"]) / "cancel").touch()
    with pytest.raises(ValueError, match="cancelled"):
        approve(tmp_path, t["id"], result["candidate_sha256"])
    (repo / "one.py").write_text(result["candidate"]["one.py"])
    result["apply_journal"] = ["one.py"]
    result["status"] = "applying"
    save(tmp_path, result)
    rollback(tmp_path, result)
    assert (repo / "one.py").read_text() == t["original"]["one.py"]


def test_real_sandbox_timeout_and_module_import(tmp_path):
    from nexora.language_sandbox import run

    (tmp_path / "helper.py").write_text("def value():return 7\n")
    out = run(
        tmp_path,
        "python",
        'from helper import value\nassert value()==7\nprint("import passed")',
    )
    assert out.startswith("Exit code: 0") and "import passed" in out
    out = run(tmp_path, "python", "while True: pass")
    assert "time limit" in out
