"""Durable, bounded Python coding workflow. Models propose; tests and owner approve."""

import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import time
import uuid

import psutil
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from nexora.artifacts import atomic_json, identifier, lock
from nexora.config import ROOT, STORE
from nexora.cowork import workspace_path
from nexora.cowork_sandbox import run_python

ROLES = {
    "planner": ["inspect", "plan"],
    "researcher": ["public_documentation"],
    "coder": ["propose_staged_file"],
    "tester": ["sandbox_test"],
    "reviewer": ["diff", "safety_review"],
}


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def folder(store, task_id):
    return Path(store) / "agent-tasks" / identifier(task_id)


def load(store, task_id):
    return json.loads((folder(store, task_id) / "task.json").read_text())


def event(task, role, action, detail):
    if task["tool_calls"] >= task.get("budget", {}).get("max_tool_calls", 24):
        raise ValueError("Task tool-call budget exceeded")
    task["events"].append(
        {"time": time.time(), "role": role, "action": action, "detail": detail}
    )
    task["tool_calls"] += 1


def save(store, task):
    atomic_json(folder(store, task["id"]) / "task.json", task)


def register(store, path):
    if not isinstance(path, str) or not path.strip():
        raise ValueError("An explicit project directory is required")
    root = Path(path).expanduser().resolve()
    if (
        not root.is_dir()
        or root == Path.home()
        or len(root.parts) < 4
        or any(root.is_relative_to(p) for p in ["/etc", "/proc", "/sys", "/dev"])
    ):
        raise ValueError("Select a specific project directory")
    ident = digest(str(root))[:16]
    location = Path(store) / "agent-repositories"
    location.mkdir(exist_ok=True)
    atomic_json(
        location / (ident + ".json"),
        {"id": ident, "path": str(root), "approved_at": time.time()},
    )
    return {"id": ident, "path": str(root)}


def repository(store, ident):
    return Path(
        json.loads(
            (
                Path(store) / "agent-repositories" / (identifier(ident) + ".json")
            ).read_text()
        )["path"]
    )


def check_python(source, local_modules=()):
    tree = ast.parse(source)
    # This first coding slice deliberately supports pure Python transforms.
    # Broader imports and application builds need a reviewed execution profile.
    allowed = {
        "math",
        "re",
        "json",
        "collections",
        "itertools",
        "statistics",
        "functools",
        "decimal",
        "fractions",
        "typing",
        "string",
    }
    allowed.update(local_modules)
    denied = {
        "eval",
        "exec",
        "compile",
        "open",
        "__import__",
        "getattr",
        "setattr",
        "delattr",
        "globals",
        "locals",
        "vars",
        "input",
        "exit",
        "quit",
        "breakpoint",
        "help",
    }
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = (
                [n.name.split(".")[0] for n in node.names]
                if isinstance(node, ast.Import)
                else [(node.module or "").split(".")[0]]
            )
            if any(n not in allowed for n in names):
                raise ValueError("Import requires a broader, reviewed sandbox profile")
        if isinstance(node, ast.Name) and (
            node.id in denied or node.id.startswith("__")
        ):
            raise ValueError(
                "Dynamic execution or introspection is outside this profile"
            )
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("Dunder introspection is outside this profile")
    return tree


def propose(
    provider, goal, original, feedback="", allow_hosted=False, prompt_style="standard"
):
    prompt = f"Replace this Python file to satisfy the goal. Return ONLY the complete pure Python function module, no explanation. Do not include tests, unittest imports or a main block; acceptance tests run separately. Allowed imports are math, re, json, collections, itertools, statistics, functools, decimal, fractions, typing and string. No filesystem access, dynamic execution or dunder introspection.\nGoal: {goal}\nCurrent file:\n{original}\nTest feedback: {feedback[-900:]}"
    if prompt_style == "concise":
        # Research remains recorded as evidence; this tiny model's context is bounded.
        error = (
            "" if feedback.startswith("Untrusted documentation") else feedback[-200:]
        )
        prompt = (
            goal
            + "\nReturn only the complete Python function, no imports or tests.\n"
            + original
            + ("\nPrevious error: " + error if error else "")
        )
    if len(prompt) > 3500:
        raise ValueError(
            "Selected source exceeds the tiny assistant context budget; choose a smaller module"
        )
    if provider == "ollama":
        from nexora.assistant_backend import generate
        text = generate("smollm2", [{"role": "user", "content": prompt}], 128 if prompt_style == "concise" else 256)["text"]
    elif provider == "qwen-coder":
        from nexora.assistant_backend import generate

        text = generate("qwen-coder", [{"role": "user", "content": prompt}], 256)[
            "text"
        ]
    elif provider == "core":
        from nexora.research import infer_run

        selected = json.loads((STORE / "selected-model.json").read_text())["id"]
        text = infer_run(selected, prompt[-256:], 96)["text"]
    elif provider == "nvidia-gpt-oss-20b" and allow_hosted:
        from nexora.nvidia_nim import request

        result = request(
            "POST",
            "/chat/completions",
            {
                "model": "openai/gpt-oss-20b",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 512,
                "temperature": 0,
            },
        )
        text = result["choices"][0]["message"]["content"]
    else:
        raise ValueError(
            "Provider unavailable or hosted inference not explicitly approved"
        )
    fences = re.findall(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    candidate = (fences[-1] if fences else text).strip() + "\n"
    if len(candidate) > 16000:
        raise ValueError("Candidate exceeds 16 KB")
    return candidate


class CodingTask(BaseModel):
    repository_id: str = Field(min_length=1, max_length=64)
    path: str = Field(min_length=1, max_length=180)
    goal: str = Field(min_length=3, max_length=1200)
    acceptance: str = Field(min_length=3, max_length=6000)
    provider: str = Field(
        default="ollama", pattern="^(ollama|core|qwen-coder|nvidia-gpt-oss-20b)$"
    )
    allow_hosted: bool = False
    prompt_style: str = Field(default="standard", pattern="^(standard|concise)$")
    max_attempts: int = Field(default=2, ge=1, le=2)
    proposed_code: str | None = Field(default=None, max_length=16000)
    documentation_url: str | None = Field(default=None, max_length=500)


def create(store, body):
    root = repository(store, body.repository_id)
    target = workspace_path(root, body.path)
    if target.suffix != ".py" or not target.is_file() or target.stat().st_size > 16000:
        raise ValueError("Select an existing Python file below 16 KB")
    original = target.read_text()
    from nexora.data_engine import SECRET

    if SECRET.search(original):
        raise ValueError(
            "Source matches private-data filter; do not send credentials to a model"
        )
    ident = uuid.uuid4().hex
    dest = folder(store, ident)
    dest.mkdir(parents=True)
    (dest / "original.py").write_text(original)
    task = {
        "id": ident,
        "status": "queued",
        "created_at": time.time(),
        "request": body.model_dump(),
        "original_sha256": digest(original),
        "events": [],
        "tool_calls": 0,
        "attempts": 0,
        "failed_attempts": 0,
        "unsafe_attempts": 0,
        "budget": {
            "max_seconds": 90,
            "max_tool_calls": 24,
            "max_attempts": body.max_attempts,
            "max_model_tokens": 1024,
            "sandbox_seconds_per_attempt": 10,
        },
        "acceptance_criteria": "Owner-supplied Python assertions must finish with exit 0 and an unmodified verifier marker; reviewer must accept scoped diff; owner must approve before original edit.",
        "model_origin": "independent Core research"
        if body.provider == "core"
        else "external reference",
        "structured_plan": [
            {
                "id": "inspect",
                "tool": "registered_source_read",
                "depends_on": [],
                "criterion": "source hash recorded",
            },
            {
                "id": "propose",
                "tool": "bounded_model_proposal",
                "depends_on": ["inspect"],
                "criterion": "staged pure Python file",
            },
            {
                "id": "test",
                "tool": "rootless_python_sandbox",
                "depends_on": ["propose"],
                "criterion": "owner assertions and fresh verifier marker",
            },
            {
                "id": "review",
                "tool": "diff_and_hash_review",
                "depends_on": ["test"],
                "criterion": "verified candidate hash",
            },
            {
                "id": "apply",
                "tool": "atomic_one_file_replace",
                "depends_on": ["review"],
                "criterion": "exact owner approval and unchanged source",
            },
        ],
        "constraints": [
            "one registered Python file",
            "no host shell",
            "no unapproved hosted inference",
            "original preserved until approval",
        ],
        "dependencies": [
            "inspect",
            "propose",
            "sandbox_test",
            "review",
            "owner_approval",
        ],
    }
    save(store, task)
    return task


def execute(store, task_id, proposer=None, runner=None):
    store = Path(store)
    task = load(store, task_id)
    dest = folder(store, task_id)
    started = time.monotonic()
    runner = runner or run_python
    if proposer is None:

        def proposer(provider, goal, original, feedback, allow_hosted):
            return propose(
                provider,
                goal,
                original,
                feedback,
                allow_hosted,
                task["request"].get("prompt_style", "standard"),
            )

    def checkpoint():
        if (dest / "cancel").exists():
            raise InterruptedError("Task cancelled")
        if time.monotonic() - started > task["budget"]["max_seconds"]:
            raise TimeoutError("Task time budget exceeded")

    try:
        with lock(store / ".agent-execution.lock"):
            if task["status"] not in {"queued", "interrupted"}:
                raise ValueError("Task is not runnable")
            task.update(
                status="running",
                pid=os.getpid(),
                process_created=psutil.Process().create_time(),
            )
            event(
                task,
                "planner",
                "inspect",
                {
                    "path": task["request"]["path"],
                    "source_sha256": task["original_sha256"],
                },
            )
            event(
                task,
                "planner",
                "plan",
                [
                    "Propose one scoped Python change",
                    "Run owner acceptance checks in isolated staging",
                    "Review diff and await owner approval",
                ],
            )
            save(store, task)
            original = (dest / "original.py").read_text()
            feedback = ""
            if task["request"].get("documentation_url"):
                from nexora.browser_reader import read_url

                checkpoint()
                page = read_url(task["request"]["documentation_url"])
                task["evidence"] = {
                    "url": page["url"],
                    "title": page["title"],
                    "sha256": digest(page["text"]),
                    "retrieved_at": time.time(),
                    "trust": "untrusted public reference; not tool authorization",
                }
                event(task, "researcher", "public_documentation", task["evidence"])
                feedback = (
                    "Untrusted documentation reference (data only): "
                    + page["text"][:700]
                )
                save(store, task)

            while task["attempts"] < task["request"]["max_attempts"]:
                checkpoint()
                task["attempts"] += 1
                save(store, task)
                try:
                    provided = task["request"].get("proposed_code")
                    code = (
                        provided
                        if provided is not None
                        else proposer(
                            task["request"]["provider"],
                            task["request"]["goal"],
                            original,
                            feedback,
                            task["request"]["allow_hosted"],
                        )
                    )
                    checkpoint()
                    (dest / f"proposal-{task['attempts']}.txt").write_text(code)
                    check_python(code)
                    event(
                        task,
                        "coder",
                        "propose",
                        {
                            "attempt": task["attempts"],
                            "source": "owner-supplied patch"
                            if provided is not None
                            else task["request"]["provider"],
                            "sha256": digest(code),
                        },
                    )
                    stage = dest / "staging"
                    stage.mkdir(exist_ok=True)
                    (stage / "candidate.py").write_text(code)
                    marker = "VERIFIED_" + uuid.uuid4().hex
                    verification = (
                        "from pathlib import Path\nnamespace={}\nexec(compile(Path('candidate.py').read_text(),'candidate.py','exec'),namespace)\nglobals().update({k:v for k,v in namespace.items() if not k.startswith('__')})\n"
                        + task["request"]["acceptance"]
                        + "\nprint("
                        + repr(marker)
                        + ")\n"
                    )
                    (stage / "verify.py").write_text(verification)
                    result = runner(stage, stage / "verify.py")
                    checkpoint()
                    passed = result.startswith("Exit code: 0\n") and marker in result
                    event(
                        task,
                        "tester",
                        "sandbox_test",
                        {
                            "passed": passed,
                            "output": result.replace(marker, "VERIFICATION_MARKER")[
                                -4000:
                            ],
                        },
                    )
                    if not passed:
                        raise ValueError("Acceptance checks failed: " + result[-900:])
                    patch = "".join(
                        difflib.unified_diff(
                            original.splitlines(True),
                            code.splitlines(True),
                            fromfile="a/" + task["request"]["path"],
                            tofile="b/" + task["request"]["path"],
                        )
                    )
                    if not patch:
                        raise ValueError("Candidate made no change")
                    task.update(
                        status="awaiting_approval",
                        diff=patch,
                        candidate_sha256=digest(code),
                        verification={
                            "passed": True,
                            "profile": "pure-python-rootless",
                            "claim_kind": "verified_by_execution",
                        },
                    )
                    (dest / "candidate.py").write_text(code)
                    event(
                        task,
                        "reviewer",
                        "review",
                        {
                            "decision": "scoped candidate passed syntax, permission profile and acceptance checks; owner review required",
                            "sha256": digest(code),
                        },
                    )
                    break
                except (ValueError, SyntaxError, HTTPException) as exc:
                    feedback = str(exc)
                    task["failed_attempts"] += 1
                    if "profile" in feedback or "introspection" in feedback:
                        task["unsafe_attempts"] += 1
                    event(task, "reviewer", "revise", {"reason": feedback[:1200]})
                    save(store, task)
                    if task["request"].get("proposed_code") is not None:
                        break
            if task["status"] == "running":
                task.update(status="failed", error=feedback)
    except InterruptedError as exc:
        task.update(status="cancelled", error=str(exc))
    except Exception as exc:
        task.update(status="failed", error=type(exc).__name__ + ": " + str(exc)[:500])
    finally:
        task.update(
            seconds=time.monotonic() - started,
            peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        )
        save(store, task)
    return task


def approve(store, task_id, candidate_sha256):
    dest = folder(store, task_id)
    with lock(dest / ".approval.lock"):
        task = load(store, task_id)
        if (
            task["status"] != "awaiting_approval"
            or task.get("candidate_sha256") != candidate_sha256
        ):
            raise ValueError("No matching verified candidate awaiting approval")
        if (dest / "cancel").exists():
            raise ValueError("Task cancelled")
        target = workspace_path(
            repository(store, task["request"]["repository_id"]), task["request"]["path"]
        )
        code = (dest / "candidate.py").read_text()
        if (
            digest(code) != candidate_sha256
            or digest(target.read_text()) != task["original_sha256"]
        ):
            raise ValueError(
                "Source or candidate changed since verification; re-run review"
            )
        check_python(code)
        task["status"] = "applying"
        event(task, "reviewer", "owner_approval_recorded", {"sha256": candidate_sha256})
        save(store, task)
        # One file, atomic replace; backup remains immutable in the task directory.
        temporary = target.with_name(target.name + ".nexora-tmp")
        with temporary.open("x") as stream:
            stream.write(code)
        temporary.chmod(target.stat().st_mode & 0o777)
        temporary.replace(target)
        task["status"] = "completed"
        event(task, "reviewer", "owner_approved_apply", {"sha256": candidate_sha256})
        save(store, task)
    return task


def launch(store, task_id):
    dest = folder(store, task_id)
    with (dest / "worker.log").open("ab") as log:
        proc = subprocess.Popen(
            [sys.executable, "-m", "nexora.agent_runtime", str(store), task_id],
            cwd=ROOT,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
    atomic_json(
        dest / "worker.json",
        {"pid": proc.pid, "created": psutil.Process(proc.pid).create_time()},
    )
    return proc.pid


def router(store):
    routes = APIRouter(prefix="/api/agent", tags=["bounded coding agent"])

    def safe(fn, *args):
        try:
            return fn(*args)
        except (ValueError, OSError, KeyError) as exc:
            raise HTTPException(409, str(exc)) from exc

    @routes.get("/roles")
    def roles():
        return ROLES

    @routes.post("/repositories", status_code=201)
    def repositories(body: dict):
        return safe(register, store, body.get("path", ""))

    @routes.get("/repositories")
    def repositories_list():
        return [
            json.loads(p.read_text())
            for p in (Path(store) / "agent-repositories").glob("*.json")
        ]

    @routes.get("/repositories/{ident}/files")
    def source_files(ident: str, q: str = ""):
        root = safe(repository, store, ident)
        if len(q) > 100:
            raise HTTPException(422, "Search query exceeds budget")
        entries = []
        visited = 0
        for current, dirs, files in os.walk(root):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d
                not in {"node_modules", "artifacts", "dist", "build", "__pycache__"}
                and not (Path(current) / d).is_symlink()
            ]
            for name in files:
                visited += 1
                if visited > 2000:
                    break
                path = Path(current) / name
                rel = path.relative_to(root)
                if (
                    name.startswith(".")
                    or path.is_symlink()
                    or path.suffix not in {".py", ".js", ".ts", ".tsx", ".php", ".md"}
                ):
                    continue
                if q.lower() not in str(rel).lower():
                    continue
                entries.append({"path": str(rel), "bytes": path.stat().st_size})
                if len(entries) >= 200:
                    break
            if visited > 2000 or len(entries) >= 200:
                break
        return {
            "files": entries,
            "limit": 200,
            "scope": "registered repository; hidden files and symlinks excluded",
        }

    @routes.get("/repositories/{ident}/source")
    def source_read(ident: str, path: str):
        root = safe(repository, store, ident)
        target = safe(workspace_path, root, path)
        if (
            target.suffix not in {".py", ".js", ".ts", ".tsx", ".php", ".md"}
            or not target.is_file()
            or target.stat().st_size > 16000
        ):
            raise HTTPException(409, "Unsupported source type or size")
        text = safe(target.read_text)
        from nexora.data_engine import SECRET

        if SECRET.search(text):
            raise HTTPException(403, "Source matches private-data filter")
        symbols = []
        if target.suffix == ".py":
            try:
                symbols = [
                    n.name
                    for n in ast.walk(ast.parse(text))
                    if isinstance(
                        n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                    )
                ]
            except SyntaxError:
                pass
        return {
            "path": path,
            "text": text,
            "sha256": digest(text),
            "python_symbols": symbols,
            "permission_authority": False,
        }

    @routes.post("/tasks", status_code=202)
    def tasks(body: CodingTask):
        task = safe(create, store, body)
        launch(store, task["id"])
        return task

    @routes.get("/tasks")
    def tasks_list():
        return [
            json.loads(p.read_text())
            for p in sorted(
                (Path(store) / "agent-tasks").glob("*/task.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )[:50]
        ]

    @routes.get("/tasks/{ident}")
    def task_get(ident: str):
        task = safe(load, store, ident)
        if task["status"] == "applying":
            target = workspace_path(
                repository(store, task["request"]["repository_id"]),
                task["request"]["path"],
            )
            current = digest(target.read_text())
            if current == task["candidate_sha256"]:
                task["status"] = "completed"
                event(task, "reviewer", "recover_recorded_apply", {"sha256": current})
            elif current == task["original_sha256"]:
                task["status"] = "awaiting_approval"
            else:
                task.update(
                    status="failed",
                    error="Source conflict during apply recovery; owner inspection required",
                )
            save(store, task)
        if (
            task["status"] == "queued"
            and (folder(store, ident) / "worker.json").exists()
        ):
            worker = json.loads((folder(store, ident) / "worker.json").read_text())
            try:
                alive = (
                    psutil.Process(worker["pid"]).create_time() == worker["created"]
                    and psutil.Process(worker["pid"]).status() != psutil.STATUS_ZOMBIE
                )
            except psutil.NoSuchProcess:
                alive = False
            if not alive:
                task["status"] = "interrupted"
                save(store, task)
        if task["status"] == "running":
            try:
                alive = (
                    psutil.Process(task["pid"]).create_time() == task["process_created"]
                    and psutil.Process(task["pid"]).status() != psutil.STATUS_ZOMBIE
                )
            except (psutil.NoSuchProcess, KeyError):
                alive = False
            if not alive:
                task["status"] = "interrupted"
                save(store, task)
        return task

    @routes.post("/tasks/{ident}/cancel")
    def cancel(ident: str):
        task = safe(load, store, ident)
        (folder(store, ident) / "cancel").touch()
        if task["status"] in {"queued", "awaiting_approval", "interrupted"}:
            task["status"] = "cancelled"
            save(store, task)
        return {
            "cancel_requested": True,
            "latency_bound": "Current model call or sandbox budget, then next checkpoint; no host edit is permitted",
        }

    @routes.post("/tasks/{ident}/approve")
    def task_approve(ident: str, body: dict):
        return safe(approve, store, ident, body.get("candidate_sha256"))

    @routes.post("/tasks/{ident}/resume")
    def resume(ident: str):
        task = task_get(ident)
        if task["status"] != "interrupted":
            raise HTTPException(409, "Only interrupted work can resume")
        if task["attempts"] >= task["request"]["max_attempts"]:
            raise HTTPException(409, "Attempt budget exhausted")
        launch(store, ident)
        return {"resuming": True}

    return routes


if __name__ == "__main__":
    execute(Path(sys.argv[1]), sys.argv[2])
