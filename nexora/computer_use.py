"""Reviewed, durable browser workflows: public read or fixed disposable local form."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import psutil
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from nexora.artifacts import atomic_json, identifier, lock, sha256
from nexora.browser_reader import _validate_url

FIXTURE = "http://127.0.0.1:8000/api/computer/fixture"
HTML = """<!doctype html><html><head><title>NEXORA disposable form</title></head>
<body><h1>Local test application</h1><label for="name">Display name</label>
<input id="name" maxlength="80"><button id="submit" type="button">Preview greeting</button>
<output id="result"></output><p>Test data only. No login, uploads or messages are sent.</p>
<script>document.querySelector('#submit').onclick=()=>{document.querySelector('#result').textContent='Hello, '+document.querySelector('#name').value.trim()+'!';};</script></body></html>"""


class BrowserTask(BaseModel):
    profile: str = Field(default="fixture", pattern="^(fixture|public-read)$")
    value: str = Field(default="NEXORA", min_length=1, max_length=80)
    url: str | None = Field(default=None, max_length=2000)
    expected: str | None = Field(default=None, min_length=1, max_length=200)


class Approval(BaseModel):
    plan_sha256: str = Field(min_length=64, max_length=64)


def location(store, ident):
    return Path(store) / "computer-tasks" / identifier(ident)


def write(store, task):
    atomic_json(location(store, task["id"]) / "task.json", task)


def read(store, ident):
    return json.loads((location(store, ident) / "task.json").read_text())


def create(store, body):
    from nexora.data_engine import SECRET

    if SECRET.search(body.value):
        raise ValueError("Do not put credentials in the test fixture")
    if body.profile == "public-read":
        if not body.url or not body.expected:
            raise ValueError("Public read requires a URL and expected visible text")
        _validate_url(body.url)
        actions = [
            ("navigate", body.url),
            ("inspect", None),
            ("assert_text", body.expected),
            ("screenshot", None),
        ]
    else:
        actions = [
            ("navigate", FIXTURE),
            ("type", body.value),
            ("click", "#submit"),
            ("assert_text", f"Hello, {body.value.strip()}!"),
            ("screenshot", None),
        ]
    plan = [
        {
            "id": str(i),
            "depends_on": [str(i - 1)] if i else [],
            "action": action,
            "value": value,
            "timeout_ms": 5000,
        }
        for i, (action, value) in enumerate(actions)
    ]
    digest = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    task = {
        "id": uuid.uuid4().hex,
        "status": "awaiting_approval",
        "profile": body.profile,
        "goal": "Verify disposable form greeting"
        if body.profile == "fixture"
        else "Read public page and verify visible text",
        "plan": plan,
        "plan_sha256": digest,
        "max_seconds": 35,
        "max_attempts": 2,
        "attempts": 0,
        "events": [],
        "evidence": [],
        "created": time.time(),
        "policy": "No personal profiles, login, uploads, messages, purchases, deletion, host commands or external interactive forms",
    }
    location(store, task["id"]).mkdir(parents=True)
    write(store, task)
    return task


def recover(store, ident):
    task = read(store, ident)
    if task["status"] in {"running", "queued"}:
        try:
            p = psutil.Process(task["pid"])
            alive = (
                p.is_running()
                and p.status() != psutil.STATUS_ZOMBIE
                and abs(p.create_time() - task["process_created"]) < 0.01
            )
        except (psutil.Error, KeyError):
            alive = False
        if not alive:
            task["status"] = "interrupted"
            write(store, task)
    return task


def checkpoint(store, task, started):
    if (location(store, task["id"]) / "cancel").exists():
        raise InterruptedError("Owner cancelled task")
    if time.monotonic() - started > task["max_seconds"]:
        raise TimeoutError("Browser task time budget exceeded")
    if psutil.virtual_memory().available < 350 * 1024**2:
        raise RuntimeError("Insufficient available RAM for browser")


def execute(store, ident):
    from playwright.sync_api import sync_playwright

    store = Path(store)
    dest = location(store, ident)
    started = time.monotonic()
    task = read(store, ident)
    if task["status"] != "queued" or task.get("approved_sha256") != task["plan_sha256"]:
        raise ValueError("Exact plan approval is required")
    actual = hashlib.sha256(
        json.dumps(task["plan"], sort_keys=True).encode()
    ).hexdigest()
    if actual != task["plan_sha256"]:
        raise ValueError("Plan changed after approval")
    task.update(
        status="running",
        pid=os.getpid(),
        process_created=psutil.Process().create_time(),
        attempts=task["attempts"] + 1,
    )
    write(store, task)
    cpu_start = sum(psutil.Process().cpu_times()[:2])
    try:
        with lock(store / ".computer-execution.lock"), sync_playwright() as p:
            checkpoint(store, task, started)
            browser = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
            try:
                context = browser.new_context(
                    accept_downloads=False,
                    service_workers="block",
                    java_script_enabled=task["profile"] == "fixture",
                    viewport={"width": 1000, "height": 700},
                )
                context.clear_permissions()
                page = context.new_page()
                page.set_default_timeout(5000)
                page.on("popup", lambda popup: popup.close())
                navigations = [0]

                def guard(route):
                    request = route.request
                    try:
                        checkpoint(store, task, started)
                        if (
                            request.method != "GET"
                            or request.resource_type != "document"
                        ):
                            raise ValueError("Only document GET requests allowed")
                        navigations[0] += 1
                        if navigations[0] > 8:
                            raise ValueError("Navigation limit exceeded")
                        if task["profile"] == "fixture":
                            if request.url != FIXTURE:
                                raise ValueError("Outside fixed disposable app")
                        else:
                            _validate_url(request.url)
                        route.continue_()
                    except (ValueError, RuntimeError, TimeoutError, InterruptedError):
                        route.abort()

                context.route("**/*", guard)
                done = set()
                for step in task["plan"]:
                    if not set(step["depends_on"]).issubset(done):
                        raise ValueError("Unmet step dependency")
                    checkpoint(store, task, started)
                    action = step["action"]
                    if action == "navigate":
                        page.goto(
                            step["value"], wait_until="domcontentloaded", timeout=5000
                        )
                    elif action == "inspect":
                        text = page.inner_text("body")[:20000]
                        task["evidence"].append(
                            {
                                "kind": "public-text",
                                "url": page.url,
                                "title": page.title(),
                                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                                "excerpt": text[:1000],
                                "retrieved_at": time.time(),
                                "trust": "untrusted data",
                            }
                        )
                    elif action == "type" and task["profile"] == "fixture":
                        page.locator("#name").fill(step["value"])
                    elif action == "click" and task["profile"] == "fixture":
                        page.locator("#submit").click()
                    elif action == "assert_text":
                        visible = (
                            page.locator("#result").inner_text()
                            if task["profile"] == "fixture"
                            else page.inner_text("body")
                        )
                        if step["value"] not in visible:
                            raise ValueError("Expected visible text was absent")
                        task["evidence"].append(
                            {
                                "kind": "assertion",
                                "expected": step["value"],
                                "passed": True,
                            }
                        )
                    elif action == "screenshot":
                        image = dest / f"attempt-{task['attempts']}.png"
                        page.screenshot(path=str(image))
                        task["evidence"].append(
                            {
                                "kind": "screenshot",
                                "file": image.name,
                                "sha256": sha256(image),
                            }
                        )
                    else:
                        raise ValueError("Action is not allowed in this profile")
                    done.add(step["id"])
                    task["events"].append(
                        {
                            "step": step["id"],
                            "action": action,
                            "status": "verified",
                            "time": time.time(),
                        }
                    )
                    task["peak_tree_rss_mb"] = max(
                        task.get("peak_tree_rss_mb", 0),
                        sum(
                            proc.memory_info().rss
                            for proc in [
                                psutil.Process(),
                                *psutil.Process().children(recursive=True),
                            ]
                            if proc.is_running()
                        )
                        / 1024**2,
                    )
                    write(store, task)
                checkpoint(store, task, started)
                task["status"] = "completed"
                task["verification"] = {
                    "assertion": True,
                    "screenshot": True,
                    "claim": "DOM assertion passed; screenshot retained as visual evidence, not an independent semantic image judge",
                }
            finally:
                browser.close()
    except InterruptedError as exc:
        task.update(status="cancelled", error=str(exc))
    except Exception as exc:
        task.update(status="failed", error=type(exc).__name__ + ": " + str(exc)[:400])
    task.update(
        seconds=time.monotonic() - started,
        worker_cpu_seconds=sum(psutil.Process().cpu_times()[:2]) - cpu_start,
    )
    write(store, task)
    return task


def authorize(store, ident, digest):
    dest = location(store, ident)
    if not (dest / "task.json").is_file():
        raise FileNotFoundError("Task not found")
    with lock(dest / ".state.lock"):
        task = recover(store, ident)
        if (
            task["status"] not in {"awaiting_approval", "interrupted", "failed"}
            or task["attempts"] >= task["max_attempts"]
            or (dest / "cancel").exists()
        ):
            raise ValueError("Task cannot be started or retried")
        if (
            digest != task["plan_sha256"]
            or digest
            != hashlib.sha256(
                json.dumps(task["plan"], sort_keys=True).encode()
            ).hexdigest()
        ):
            raise ValueError("Approval does not match plan")
        task.update(status="queued", approved_sha256=digest)
        # Persist and publish PID before worker can acquire the per-task state lock.
        write(store, task)
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "nexora.computer_use",
                "--store",
                str(store),
                "--task",
                ident,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=Path(__file__).resolve().parent.parent,
            start_new_session=True,
        )
        task.update(
            pid=proc.pid, process_created=psutil.Process(proc.pid).create_time()
        )
        write(store, task)
        return task


def router(store):
    routes = APIRouter(prefix="/api/computer", tags=["isolated browser tasks"])

    @routes.get("/fixture", response_class=HTMLResponse)
    def fixture():
        return HTML

    @routes.post("/tasks", status_code=201)
    def new(body: BrowserTask):
        try:
            return create(store, body)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @routes.get("/tasks")
    def tasks():
        root = Path(store) / "computer-tasks"
        return [
            recover(store, p.name)
            for p in sorted(
                root.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True
            )[:30]
            if p.is_dir() and (p / "task.json").is_file()
        ]

    @routes.get("/tasks/{ident}")
    def task(ident: str):
        try:
            return recover(store, ident)
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(404, "Task not found") from exc

    @routes.post("/tasks/{ident}/approve")
    def approval(ident: str, body: Approval):
        try:
            return authorize(store, ident, body.plan_sha256)
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(409, str(exc)) from exc

    @routes.post("/tasks/{ident}/cancel")
    def cancel(ident: str):
        try:
            read(store, ident)
            with lock(location(store, ident) / ".state.lock"):
                task = recover(store, ident)
                if task["status"] in {"completed", "cancelled"}:
                    return task
                (location(store, ident) / "cancel").touch()
                if task["status"] in {"awaiting_approval", "interrupted", "failed"}:
                    task["status"] = "cancelled"
                    write(store, task)
                return task
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(404, "Task not found") from exc

    @routes.get("/tasks/{ident}/screenshot")
    def screenshot(ident: str):
        try:
            task_result = read(store, identifier(ident))
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(404, "Task not found") from exc
        evidence = [e for e in task_result["evidence"] if e["kind"] == "screenshot"]
        if not evidence:
            raise HTTPException(404, "No screenshot")
        path = location(store, ident) / evidence[-1]["file"]
        if sha256(path) != evidence[-1]["sha256"]:
            raise HTTPException(409, "Screenshot integrity check failed")
        return FileResponse(path, media_type="image/png")

    return routes


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", required=True)
    parser.add_argument("--task", required=True)
    args = parser.parse_args()
    for attempt in range(50):
        try:
            with lock(location(args.store, args.task) / ".state.lock"):
                break
        except ValueError:
            time.sleep(0.05)
    else:
        raise RuntimeError("Task state lock unavailable")
    execute(args.store, args.task)
