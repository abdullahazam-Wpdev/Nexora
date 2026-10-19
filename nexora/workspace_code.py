"""Minimal multi-file proposals; fixed profiles, isolated tests, exact-hash apply journal."""

import psutil
import difflib, hashlib, json, os, re, subprocess, sys, time, uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from nexora.agent_runtime import repository, check_python
from nexora.artifacts import atomic_json, identifier, lock
from nexora.cowork import workspace_path
from nexora.assistant_backend import generate
from nexora.language_sandbox import run


class Task(BaseModel):
    repository_id: str = Field(min_length=1, max_length=64)
    files: list[str] = Field(min_length=1, max_length=4)
    goal: str = Field(min_length=3, max_length=1200)
    acceptance: str = Field(min_length=3, max_length=6000)
    profile: str = Field(
        pattern="^(python|node|typescript|next-route|html|php|fastapi)$"
    )
    model: str = Field(default="qwen-coder", pattern="^(qwen-coder|smollm2)$")
    max_attempts: int = Field(default=2, ge=1, le=2)


def folder(store, ident):
    return Path(store) / "workspace-code" / identifier(ident)


def digest(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def read(store, ident):
    return json.loads((folder(store, ident) / "task.json").read_text())


def save(store, task):
    atomic_json(folder(store, task["id"]) / "task.json", task)


def validate(files, original, profile):
    if not isinstance(files, dict) or not files or set(files) - set(original):
        raise ValueError("Patch changed files outside the approved scope")
    for path, text in files.items():
        if not isinstance(text, str) or len(text) > 8000:
            raise ValueError("Candidate file exceeds budget")
        if path.endswith(".py") and profile == "python":
            check_python(text)
        if path.endswith((".js", ".ts")) and re.search(
            r'\b(?:process|eval|Function|globalThis|Reflect)\b|__proto__|\.constructor|require\s*\(\s*[\'"](?!\./)',
            text,
        ):
            raise ValueError(
                "JS execution/introspection/import outside the pure module profile"
            )
    if all(original[p] == v for p, v in files.items()):
        raise ValueError("No source change")


def create(store, body):
    from nexora.data_engine import SECRET

    root = repository(store, body.repository_id)
    original = {}
    for name in body.files:
        if name in original or name.startswith(("acceptance", "verify")):
            raise ValueError("Duplicate or reserved path")
        p = workspace_path(root, name)
        if (
            not p.is_file()
            or p.suffix not in {".py", ".js", ".ts", ".html", ".css", ".md", ".php"}
            or p.stat().st_size > 8000
        ):
            raise ValueError("Unsupported source path/size")
        text = p.read_text()
        if SECRET.search(text):
            raise ValueError("Source matches credential/private-data filter")
        original[name] = text
    if len(json.dumps(original)) + len(body.goal) > 3000:
        raise ValueError(
            "Context exceeds tiny assistant budget; scope the task more narrowly"
        )
    task = {
        "id": uuid.uuid4().hex,
        "status": "queued",
        "request": body.model_dump(),
        "original": original,
        "original_sha256": digest(original),
        "attempts": 0,
        "events": [],
        "created": time.time(),
        "claim": "Tests must pass; exact approval required before original edits",
        "budget": {"seconds": 90, "attempts": body.max_attempts, "sandbox_seconds": 10},
    }
    folder(store, task["id"]).mkdir(parents=True)
    save(store, task)
    return task


def execute(store, ident, proposer=None):
    task = read(store, ident)
    dest = folder(store, ident)
    started = time.monotonic()
    feedback = ""
    if task["request"]["profile"] in {"php", "fastapi"}:
        task.update(
            status="blocked",
            error="No verified runtime for this profile; not scored as a pass",
        )
        save(store, task)
        return task
    try:
        with lock(Path(store) / ".workspace-code.lock"):
            if task["status"] != "queued":
                raise ValueError("Task is not queued")
            task.update(
                status="running",
                pid=os.getpid(),
                process_created=psutil.Process().create_time(),
            )
            save(store, task)
            for attempt in range(task["attempts"], task["request"]["max_attempts"]):
                if (dest / "cancel").exists():
                    raise InterruptedError("Task cancelled")
                if time.monotonic() - started > 90:
                    raise TimeoutError("Task deadline")
                task["attempts"] += 1
                prompt = (
                    'Repair only the supplied files. Return ONLY JSON {"files":{"path":"complete updated text"}}. No tests or explanations.\nGoal: '
                    + task["request"]["goal"]
                    + "\nFiles: "
                    + json.dumps(task["original"])
                    + "\nFailure: "
                    + feedback[-400:]
                )
                try:
                    if proposer:
                        files = proposer(task, prompt)
                    else:
                        schema = {
                            "type": "object",
                            "properties": {
                                "files": {
                                    "type": "object",
                                    "properties": {
                                        name: {"type": "string"}
                                        for name in task["original"]
                                    },
                                    "additionalProperties": False,
                                    "minProperties": 1,
                                }
                            },
                            "required": ["files"],
                            "additionalProperties": False,
                        }
                        single = len(task["original"]) == 1
                        if single:
                            name = next(iter(task["original"]))
                            prompt = (
                                task["request"]["goal"]
                                + "\nReturn only the complete corrected file; no explanation or tests.\n"
                                + task["original"][name]
                                + (
                                    "\nPrevious error: " + feedback[-200:]
                                    if feedback
                                    else ""
                                )
                            )
                        (dest / f"prompt-{task['attempts']}.txt").write_text(prompt)
                        result = generate(
                            task["request"]["model"],
                            [{"role": "user", "content": prompt}],
                            256,
                            output_schema=None if single else schema,
                        )
                        task["inference"] = result
                        (dest / f"model-response-{task['attempts']}.txt").write_text(
                            result["text"]
                        )
                        raw = result["text"]
                        if single:
                            fences = re.findall(r"```[^\n]*\n(.*?)```", raw, re.S)
                            files = {
                                name: (fences[-1] if fences else raw).strip() + "\n"
                            }
                        else:
                            fences = re.findall(r"```(?:json)?\s*\n(.*?)```", raw, re.S)
                            parsed = json.loads(fences[-1] if fences else raw)
                            if not isinstance(parsed, dict) or set(parsed) != {"files"}:
                                raise ValueError("Expected one files object")
                            files = parsed["files"]
                        task["inference"] = result
                    (dest / f"proposal-{task['attempts']}.json").write_text(
                        json.dumps(files, indent=2)
                    )
                    validate(files, task["original"], task["request"]["profile"])
                    stage = dest / "staging"
                    stage.mkdir(exist_ok=True)
                    for name, text in {**task["original"], **files}.items():
                        p = workspace_path(stage, name)
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.write_text(text)
                    marker = "VERIFIED_" + uuid.uuid4().hex
                    script = (
                        task["request"]["acceptance"]
                        + "\n"
                        + (
                            "console.log(" + json.dumps(marker) + ");"
                            if task["request"]["profile"]
                            in {"node", "typescript", "next-route"}
                            else "print(" + repr(marker) + ")"
                        )
                    )
                    output = run(stage, task["request"]["profile"], script)
                    passed = output.startswith("Exit code: 0\n") and marker in output
                    task["events"].append(
                        {
                            "attempt": attempt + 1,
                            "passed": passed,
                            "output": output.replace(marker, "VERIFIER_MARKER")[-2000:],
                        }
                    )
                    if not passed:
                        raise ValueError(output[-500:])
                    if (dest / "cancel").exists():
                        raise InterruptedError("Task cancelled after testing")
                    diff = "".join(
                        "".join(
                            difflib.unified_diff(
                                task["original"][p].splitlines(True),
                                v.splitlines(True),
                                fromfile="a/" + p,
                                tofile="b/" + p,
                            )
                        )
                        for p, v in files.items()
                    )
                    task.update(
                        status="awaiting_approval",
                        candidate=files,
                        candidate_sha256=digest(files),
                        diff=diff,
                        verification={
                            "passed": True,
                            "profile": task["request"]["profile"],
                        },
                    )
                    break
                except (ValueError, HTTPException, SyntaxError) as exc:
                    feedback = str(exc)
                    task["events"].append(
                        {"attempt": attempt + 1, "failure": feedback[:1000]}
                    )
                    save(store, task)
            if task["status"] in {"running", "queued"} and "pid" in task:
                task.update(status="failed", error=feedback)
    except InterruptedError as exc:
        task.update(status="cancelled", error=str(exc))
    except Exception as exc:
        task.update(status="failed", error=str(exc)[:500])
    task["seconds"] = time.monotonic() - started
    save(store, task)
    return task


def approve(store, ident, expected):
    dest = folder(store, ident)
    with lock(dest / ".approval.lock"):
        task = read(store, ident)
        if (
            task["status"] != "awaiting_approval"
            or task.get("candidate_sha256") != expected
            or digest(task["candidate"]) != expected
        ):
            raise ValueError("Exact verified candidate hash required")
        if (dest / "cancel").exists():
            raise ValueError("Task cancelled")
        root = repository(store, task["request"]["repository_id"])
        actual = {p: workspace_path(root, p).read_text() for p in task["original"]}
        if digest(actual) != task["original_sha256"]:
            raise ValueError("Original sources changed; rerun task")
        task.update(status="applying", apply_journal=[])
        save(store, task)
        try:
            for name, text in task["candidate"].items():
                target = workspace_path(root, name)
                if target.read_text() != task["original"][name]:
                    raise ValueError("Source changed during apply; rollback required")
                temp = target.with_name(target.name + ".nexora-" + task["id"] + ".tmp")
                with temp.open("x") as f:
                    f.write(text)
                # Journal intent first, so crash recovery can restore every touched file.
                task["apply_journal"].append(name)
                save(store, task)
                os.replace(temp, target)
            task["status"] = "completed"
            save(store, task)
        except Exception:
            rollback(store, task)
            raise
        return task


def rollback(store, task):
    root = repository(store, task["request"]["repository_id"])
    for name in task.get("apply_journal", []):
        target = workspace_path(root, name)
        if target.read_text() not in {task["original"][name], task["candidate"][name]}:
            raise ValueError("Recovery found external edits; manual review required")
        temp = target.with_name(target.name + ".nexora-rollback")
        with temp.open("x") as f:
            f.write(task["original"][name])
        os.replace(temp, target)
    task.update(
        status="interrupted", error="Apply transaction rolled back to originals"
    )
    save(store, task)


def launch(store, task):
    with lock(folder(store, task["id"]) / ".state.lock"):
        process = subprocess.Popen(
            [sys.executable, "-m", "nexora.workspace_code", str(store), task["id"]],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        task.update(
            pid=process.pid, process_created=psutil.Process(process.pid).create_time()
        )
        save(store, task)
    return task


def router(store):
    routes = APIRouter(prefix="/api/workspace-code", tags=["scoped multi-file coding"])

    @routes.post("/tasks", status_code=201)
    def new(body: Task):
        try:
            task = create(store, body)
            return launch(store, task)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @routes.get("/tasks/{ident}")
    def get(ident: str):
        try:
            task = read(store, ident)
            if task["status"] == "applying":
                try:
                    with lock(folder(store, ident) / ".approval.lock"):
                        task = read(store, ident)
                        if task["status"] == "applying":
                            rollback(store, task)
                except ValueError:
                    pass
            if task["status"] in {"running", "queued"} and "pid" in task:
                try:
                    proc = psutil.Process(task["pid"])
                    alive = (
                        proc.is_running()
                        and proc.status() != psutil.STATUS_ZOMBIE
                        and abs(proc.create_time() - task["process_created"]) < 0.01
                    )
                except (psutil.Error, KeyError):
                    alive = False
                if not alive:
                    task["status"] = "interrupted"
                    save(store, task)
            return task
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(404, str(exc)) from exc

    @routes.post("/tasks/{ident}/approve")
    def apply(ident: str, body: dict):
        try:
            return approve(store, ident, body.get("candidate_sha256"))
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(409, str(exc)) from exc

    @routes.post("/tasks/{ident}/cancel")
    def cancel(ident: str):
        try:
            task = read(store, ident)
            if task["status"] in {"completed", "cancelled"}:
                return task
            (folder(store, ident) / "cancel").touch()
            if task["status"] in {"queued", "awaiting_approval"}:
                task["status"] = "cancelled"
                save(store, task)
            return task
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(404, "Task not found") from exc

    @routes.post("/tasks/{ident}/resume")
    def resume(ident: str):
        try:
            task = read(store, ident)
            if (
                task["status"] != "interrupted"
                or task["attempts"] >= task["request"]["max_attempts"]
                or (folder(store, ident) / "cancel").exists()
            ):
                raise ValueError("No remaining approved retry budget")
            task["status"] = "queued"
            save(store, task)
            return launch(store, task)
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(409, str(exc)) from exc

    return routes


if __name__ == "__main__":
    for attempt in range(50):
        try:
            with lock(folder(Path(sys.argv[1]), sys.argv[2]) / ".state.lock"):
                break
        except ValueError:
            time.sleep(0.05)
    else:
        raise RuntimeError("Task state lock unavailable")
    execute(Path(sys.argv[1]), sys.argv[2])
