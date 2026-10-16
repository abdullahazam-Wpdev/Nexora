"""Bounded CPU experiments with exact resumption and independently evaluated checkpoints."""

import argparse
import hashlib
import json
import math
import os
import platform
import resource
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
import numpy as np
import psutil
import torch
from safetensors.torch import load_file, save_file
from tokenizers import Tokenizer, models, trainers, pre_tokenizers, decoders
from torch.nn import functional as F
from nexora.artifacts import atomic_json, identifier, lock, sha256
from nexora.config import STORE, ROOT
from nexora.data_engine import load_dataset
from nexora.model import Core, Config

ENGINE_VERSION = 2
PROFILES = {
    "tiny": {"dim": 64, "layers": 2, "heads": 4, "context": 64},
    "small": {"dim": 128, "layers": 4, "heads": 4, "context": 128},
}


@dataclass
class TrainConfig:
    steps: int = 200
    schedule_steps: int = 1000
    warmup_steps: int = 20
    batch_size: int = 4
    accumulation: int = 2
    learning_rate: float = 0.002
    weight_decay: float = 0.1
    seed: int = 42
    threads: int = 2
    eval_every: int = 50
    checkpoint_every: int = 100
    vocab_size: int = 1024
    max_seconds: float = 180
    max_rss_mb: int = 900
    min_available_mb: int = 500
    min_disk_mb: int = 512
    max_temperature: float = 88

    def __post_init__(self):
        for k in (
            "steps",
            "schedule_steps",
            "warmup_steps",
            "batch_size",
            "accumulation",
            "threads",
            "eval_every",
            "checkpoint_every",
        ):
            if getattr(self, k) < 1:
                raise ValueError(f"{k} must be positive")
        if (
            not 1 <= self.steps <= 2000
            or self.batch_size > 16
            or self.accumulation > 8
            or self.threads > 4
            or not 258 <= self.vocab_size <= 4096
        ):
            raise ValueError("Configuration exceeds laptop experiment limits")
        if (
            not 0 < self.learning_rate <= 0.05
            or not 0 <= self.weight_decay <= 1
            or not 1 <= self.max_seconds <= 600
            or not 128 <= self.max_rss_mb <= 1600
            or not 256 <= self.min_available_mb <= 4096
            or not 256 <= self.min_disk_mb
            or not 50 <= self.max_temperature <= 95
        ):
            raise ValueError("Invalid learning rate or resource budget")


def code_identity():
    paths = ["model.py", "research.py", "data_engine.py"]
    return hashlib.sha256(
        b"".join((ROOT / "nexora" / p).read_bytes() for p in paths)
    ).hexdigest()


def temperature():
    readings = psutil.sensors_temperatures()
    return max(
        (
            t.current
            for k, v in readings.items()
            if k in {"coretemp", "k10temp", "cpu_thermal"}
            for t in v
        ),
        default=None,
    )


class BudgetExceeded(RuntimeError):
    pass


class Monitor:
    def __init__(self, c, store, cancel_path=None):
        self.cancel_path = cancel_path
        self.c = c
        self.store = store
        self.started = time.monotonic()
        self.process = psutil.Process()
        self.peak_rss = 0
        self.max_temp = None
        self.samples = 0
        self.cpu_seconds = 0
        self.cpu_start = sum(self.process.cpu_times()[:2])

    def check(self):
        if self.cancel_path and self.cancel_path.exists():
            raise BudgetExceeded("Cancellation requested")
        rss = self.process.memory_info().rss
        self.peak_rss = max(self.peak_rss, rss)
        temp = temperature()
        self.samples += 1
        if temp is not None:
            self.max_temp = max(self.max_temp or temp, temp)
        if rss > self.c.max_rss_mb * 1024**2:
            raise BudgetExceeded("Process RSS budget exceeded")
        if psutil.virtual_memory().available < self.c.min_available_mb * 1024**2:
            raise BudgetExceeded("Available-memory floor reached")
        if psutil.disk_usage(str(self.store)).free < self.c.min_disk_mb * 1024**2:
            raise BudgetExceeded("Free-disk floor reached")
        if temp is not None and temp >= self.c.max_temperature:
            raise BudgetExceeded("CPU temperature budget reached")
        if time.monotonic() - self.started > self.c.max_seconds:
            raise BudgetExceeded("Experiment wall-time budget reached")

    def metrics(self):
        elapsed = time.monotonic() - self.started
        cpu = sum(self.process.cpu_times()[:2]) - self.cpu_start
        return {
            "wall_seconds": elapsed,
            "peak_rss_mb": max(
                self.peak_rss, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
            )
            / 1024**2,
            "cpu_seconds": cpu,
            "cpu_percent_one_core": 100 * cpu / max(elapsed, 0.001),
            "max_cpu_temperature_c": self.max_temp,
            "monitor_samples": self.samples,
        }


def create_run(dataset_id, profile="tiny", training=None, run_id=None, store=None):
    store = Path(store or STORE)
    c = (
        training
        if isinstance(training, TrainConfig)
        else TrainConfig(**(training or {}))
    )
    if profile not in PROFILES:
        raise ValueError("Unknown CPU profile; medium/large are planning-only")
    manifest, _ = load_dataset(dataset_id, store)
    run_id = identifier(
        run_id
        or time.strftime("%Y%m%d-%H%M%S", time.gmtime()) + "-" + uuid.uuid4().hex[:8]
    )
    folder = store / "runs" / run_id
    folder.mkdir(parents=True, exist_ok=False)
    try:
        git = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except subprocess.SubprocessError:
        git = "unknown"
    try:
        dirty = bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=ROOT, text=True
            ).strip()
        )
    except subprocess.SubprocessError:
        dirty = True
    run = {
        "id": run_id,
        "name": f"NEXORA Core {profile} / {manifest['name']}",
        "status": "queued",
        "engine_version": ENGINE_VERSION,
        "profile": profile,
        "dataset_id": dataset_id,
        "dataset_version": manifest["version"],
        "training": asdict(c),
        "git_commit": git,
        "git_dirty": dirty,
        "code_sha256": code_identity(),
        "created_at": time.time(),
        "hardware": {
            "platform": platform.platform(),
            "threads": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "device": "cpu",
            "precision": "float32",
        },
        "history": [],
        "steps": 0,
        "warning": "Independent next-token model; not instruction-tuned or a validated assistant.",
    }
    atomic_json(folder / "result.json", run)
    return run


def _prepare_tokens(folder, manifest, documents, c, monitor):
    started = time.monotonic()
    tokenizer = Tokenizer(models.BPE(unk_token="[UNK]"))
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tokenizer.decoder = decoders.ByteLevel()
    tokenizer.train_from_iterator(
        (d["text"] for d in documents["train"]),
        trainers.BpeTrainer(
            vocab_size=c.vocab_size,
            special_tokens=["[UNK]", "[EOS]"],
            initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
            show_progress=False,
        ),
    )
    tokenizer.save(str(folder / "tokenizer.json"))
    eos = tokenizer.token_to_id("[EOS]")
    shards = {}
    for split, docs in documents.items():
        tokens = []
        for d in docs:
            tokens.extend(tokenizer.encode(d["text"]).ids)
            tokens.append(eos)
        if len(tokens) < 3:
            raise ValueError("Dataset split has too few tokens")
        p = folder / (split + ".npy")
        np.save(p, np.array(tokens, dtype=np.uint16))
        shards[split] = {"path": p.name, "tokens": len(tokens), "sha256": sha256(p)}
        monitor.check()
    identity = {
        "dataset_version": manifest["version"],
        "tokenizer_sha256": sha256(folder / "tokenizer.json"),
        "shards": shards,
        "packing": "Contiguous tokens with EOS between documents; source-level splits already fixed",
        "dtype": "uint16",
        "preparation_seconds": time.monotonic() - started,
    }
    atomic_json(folder / "tokens.json", identity)
    return tokenizer, identity


def _mapped_tokens(folder, metadata):
    tokens = {}
    for split, info in metadata["shards"].items():
        p = folder / info["path"]
        if p.name != split + ".npy" or sha256(p) != info["sha256"]:
            raise ValueError("Token shard integrity mismatch")
        tokens[split] = np.load(p, mmap_mode="r", allow_pickle=False)
    if sha256(folder / "tokenizer.json") != metadata["tokenizer_sha256"]:
        raise ValueError("Tokenizer integrity mismatch")
    return tokens


def learning_rate(step, c):
    warm = min(1, (step + 1) / c.warmup_steps)
    progress = min(
        1, max(0, (step - c.warmup_steps) / max(1, c.schedule_steps - c.warmup_steps))
    )
    return (
        c.learning_rate * warm * (0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * progress)))
    )


def optimizer_for(model, c):
    # Tied parameters are yielded once by named_parameters.
    decay = [p for p in model.parameters() if p.ndim >= 2]
    no_decay = [p for p in model.parameters() if p.ndim < 2]
    return torch.optim.AdamW(
        [
            {"params": decay, "weight_decay": c.weight_decay},
            {"params": no_decay, "weight_decay": 0},
        ],
        lr=c.learning_rate,
    )


@torch.no_grad()
def evaluate(model, tokens, context, monitor=None):
    """Every next-token target counted exactly once, no RNG or truncated remainder."""
    was_training = model.training
    model.eval()
    total = 0.0
    count = 0
    try:
        for start in range(0, len(tokens) - 1, context):
            if monitor:
                monitor.check()
            size = min(context, len(tokens) - 1 - start)
            x = torch.from_numpy(
                np.array(tokens[start : start + size], dtype=np.int64)
            )[None]
            y = torch.from_numpy(
                np.array(tokens[start + 1 : start + size + 1], dtype=np.int64)
            )
            value = F.cross_entropy(model(x)[0], y, reduction="sum").item()
            if not math.isfinite(value):
                raise ValueError("Nonfinite evaluation loss")
            total += value
            count += size
        return {
            "loss": total / count,
            "perplexity": math.exp(min(80, total / count)),
            "tokens": count,
            "perplexity_capped": total / count > 80,
        }
    finally:
        model.train(was_training)


def _checkpoint(folder, model, optimizer, sampler, step, history, tokens_meta, run):
    started = time.monotonic()
    destination = folder / "checkpoints" / f"step-{step:07d}"
    # Never mutate a published checkpoint.
    if destination.exists():
        return json.loads((destination / "checkpoint.json").read_text()), 0
    staging = destination.with_name("." + destination.name + "-" + uuid.uuid4().hex[:6])
    staging.mkdir(parents=True)
    save_file(
        {k: v.detach().contiguous().clone() for k, v in model.state_dict().items()},
        str(staging / "model.safetensors"),
    )
    state = {
        "engine_version": ENGINE_VERSION,
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "sampler_rng": sampler.get_state(),
        "torch_rng": torch.get_rng_state(),
        "step": step,
        "history": history,
        "scheduler": {"completed_steps": step, "config": run["training"]},
        "config": asdict(model.config),
        "dataset_version": run["dataset_version"],
        "tokenizer_sha256": tokens_meta["tokenizer_sha256"],
        "code_sha256": run["code_sha256"],
    }
    torch.save(state, staging / "resume.pt")
    info = {
        "engine_version": ENGINE_VERSION,
        "step": step,
        "directory": destination.name,
        "config": asdict(model.config),
        "dataset_version": run["dataset_version"],
        "tokenizer_sha256": tokens_meta["tokenizer_sha256"],
        "code_sha256": run["code_sha256"],
        "files": {
            p.name: sha256(p)
            for p in (staging / "model.safetensors", staging / "resume.pt")
        },
    }
    atomic_json(staging / "checkpoint.json", info)
    staging.rename(destination)
    atomic_json(folder / "latest.json", info)
    return info, time.monotonic() - started


def verify_checkpoint(folder, checkpoint=None):
    folder = Path(folder)
    info = checkpoint or json.loads((folder / "latest.json").read_text())
    if info.get("engine_version") != ENGINE_VERSION:
        raise ValueError("Unsupported checkpoint version")
    if info["directory"] != f"step-{int(info['step']):07d}":
        raise ValueError("Invalid checkpoint directory")
    cp = folder / "checkpoints" / info["directory"]
    for name, digest in info["files"].items():
        if (
            name not in {"resume.pt", "model.safetensors"}
            or sha256(cp / name) != digest
        ):
            raise ValueError("Checkpoint integrity mismatch")
    if sha256(folder / "tokenizer.json") != info["tokenizer_sha256"]:
        raise ValueError("Tokenizer integrity mismatch")
    tensors = load_file(str(cp / "model.safetensors"))
    expected = Core(Config(**info["config"]))
    expected.load_state_dict(tensors, strict=True)
    if any(not torch.isfinite(t).all() for t in tensors.values()):
        raise ValueError("Nonfinite checkpoint tensors")
    if info["config"].get("tie_embeddings") and not torch.equal(
        tensors["head.weight"], tensors["embedding.weight"]
    ):
        raise ValueError("Tied checkpoint weights differ")
    return info, cp


def train_run(run_id, *, resume=False, additional_steps=None, store=None):
    store = Path(store or STORE)
    folder = store / "runs" / identifier(run_id)
    with lock(store / ".training.lock"):
        return _train_locked(folder, store, resume, additional_steps)


def _train_locked(folder, store, resume, additional_steps):
    run = json.loads((folder / "result.json").read_text())
    c = TrainConfig(**run["training"])
    if run["engine_version"] != ENGINE_VERSION:
        raise ValueError("Unsupported run version")
    if run["code_sha256"] != code_identity():
        raise ValueError("Training implementation changed; fork a new reproducible run")
    if not resume and run["status"] != "queued":
        raise ValueError("Existing run is immutable; resume or create a new run")
    torch.set_num_threads(c.threads)
    torch.manual_seed(c.seed)
    torch.use_deterministic_algorithms(True)
    monitor = Monitor(c, store, folder / "cancel.request")
    run.update(
        status="running",
        pid=os.getpid(),
        process_started=psutil.Process().create_time(),
        started_at=time.time(),
        error=None,
    )
    atomic_json(folder / "result.json", run)
    step = 0
    history = []
    checkpoint_seconds = 0.0
    train_seconds = 0.0
    data_seconds = 0.0
    tokens_processed = 0
    try:
        monitor.check()
        manifest, documents = load_dataset(run["dataset_id"], store)
        if manifest["version"] != run["dataset_version"]:
            raise ValueError("Dataset version changed")
        if resume:
            info, cp = verify_checkpoint(folder)
            state = torch.load(cp / "resume.pt", weights_only=True, map_location="cpu")
            if (
                state["scheduler"]["config"] != run["training"]
                or state["code_sha256"] != run["code_sha256"]
                or state["dataset_version"] != manifest["version"]
            ):
                raise ValueError("Checkpoint training identity mismatch")
            tokenizer = Tokenizer.from_file(str(folder / "tokenizer.json"))
            meta = json.loads((folder / "tokens.json").read_text())
            config = Config(**state["config"])
        else:
            tokenizer, meta = _prepare_tokens(folder, manifest, documents, c, monitor)
            config = Config(
                vocab_size=tokenizer.get_vocab_size(),
                **PROFILES[run["profile"]],
                tie_embeddings=True,
                init_std=0.02,
            )
        del documents
        if meta["dataset_version"] != manifest["version"]:
            raise ValueError("Token shards reference another dataset")
        arrays = _mapped_tokens(folder, meta)
        model = Core(config)
        parameters = sum(p.numel() for p in model.parameters())
        if parameters > 5_000_000:
            raise ValueError("CPU parameter budget exceeded")
        optimizer = optimizer_for(model, c)
        sampler = torch.Generator().manual_seed(c.seed + 1)
        if resume:
            model.load_state_dict(state["model"])
            optimizer.load_state_dict(state["optimizer"])
            sampler.set_state(state["sampler_rng"])
            torch.set_rng_state(state["torch_rng"])
            step = state["step"]
            history = state["history"]
            if state["scheduler"]["completed_steps"] != step:
                raise ValueError("Scheduler step mismatch")
            del state
        run.update(
            config=asdict(config),
            parameters=parameters,
            tokenizer_sha256=meta["tokenizer_sha256"],
            dataset_tokens={k: v["tokens"] for k, v in meta["shards"].items()},
        )
        count = additional_steps if additional_steps is not None else c.steps
        if not 1 <= count <= 2000:
            raise ValueError("Additional step count exceeds local limit")
        target = step + count
        starting_step = step
        train = arrays["train"]
        context = min(config.context, len(train) - 1)
        if not resume:
            run["initial_validation"] = evaluate(
                model, arrays["validation"], config.context, monitor
            )
        while step < target:
            monitor.check()
            begin = time.monotonic()
            model.train()
            optimizer.zero_grad(set_to_none=True)
            lr = learning_rate(step, c)
            for group in optimizer.param_groups:
                group["lr"] = lr
            total = 0.0
            for _ in range(c.accumulation):
                loading = time.monotonic()
                offsets = torch.randint(
                    len(train) - context, (c.batch_size,), generator=sampler
                ).tolist()
                x = torch.from_numpy(
                    np.stack([train[i : i + context] for i in offsets]).astype(np.int64)
                )
                y = torch.from_numpy(
                    np.stack([train[i + 1 : i + context + 1] for i in offsets]).astype(
                        np.int64
                    )
                )
                data_seconds += time.monotonic() - loading
                loss = (
                    F.cross_entropy(model(x).flatten(0, 1), y.flatten())
                    / c.accumulation
                )
                if not torch.isfinite(loss):
                    raise ValueError("Nonfinite training loss")
                loss.backward()
                total += loss.item()
                tokens_processed += x.numel()
            norm = torch.nn.utils.clip_grad_norm_(
                model.parameters(), 1, error_if_nonfinite=True
            )
            optimizer.step()
            step += 1
            train_seconds += time.monotonic() - begin
            # Per-step history makes comparison independent of stop/resume boundary.
            row = {
                "step": step,
                "train_loss": total,
                "lr": lr,
                "gradient_norm": float(norm),
            }
            history.append(row)
            if step % c.eval_every == 0 or step == target:
                row["validation"] = evaluate(
                    model, arrays["validation"], config.context, monitor
                )
                run.update(
                    history=history,
                    steps=step,
                    progress={
                        "target": target,
                        "tokens_this_session": tokens_processed,
                    },
                    resources=monitor.metrics(),
                )
                atomic_json(folder / "result.json", run)
                print(json.dumps(row), flush=True)
            if step % c.checkpoint_every == 0 or step == target:
                info, seconds = _checkpoint(
                    folder, model, optimizer, sampler, step, history, meta, run
                )
                checkpoint_seconds += seconds
        validation = evaluate(model, arrays["validation"], config.context, monitor)
        test = evaluate(model, arrays["test"], config.context, monitor)
        examples = []
        for prompt in ["Python is", "The function", "for i in range("]:
            monitor.check()
            ids = tokenizer.encode(prompt).ids
            generated = model.generate(torch.tensor([ids or [0]]), 32)[0].tolist()
            generated_text = tokenizer.decode(generated, skip_special_tokens=False)
            # Exact continuation containment is a limited memorization indicator.
            continuation = tokenizer.decode(
                generated[len(ids) :], skip_special_tokens=False
            )
            examples.append(
                {
                    "prompt": prompt,
                    "text": generated_text,
                    "continuation_exact_in_train": len(continuation) >= 40
                    and any(
                        continuation in json.loads(line)["text"]
                        for line in (
                            store / "datasets" / run["dataset_id"] / "train.jsonl"
                        )
                        .read_text()
                        .splitlines()
                    ),
                }
            )
        run.update(
            status="completed",
            steps=step,
            history=history,
            validation=validation,
            test=test,
            test_loss=test["loss"],
            seconds=monitor.metrics()["wall_seconds"],
            checkpoint=str(
                Path("runs")
                / run["id"]
                / "checkpoints"
                / info["directory"]
                / "model.safetensors"
            ),
            samples=examples,
            resources=monitor.metrics(),
            benchmark={
                "tokens_this_session": tokens_processed,
                "total_training_tokens": step * c.batch_size * c.accumulation * context,
                "training_seconds": train_seconds,
                "tokens_per_second": tokens_processed / max(0.0001, train_seconds),
                "step_seconds": train_seconds / max(1, step - starting_step),
                "dataset_loading_seconds": data_seconds,
                "checkpoint_save_seconds": checkpoint_seconds,
                "estimated_1000_step_seconds": 1000
                * train_seconds
                / max(1, step - starting_step),
            },
            completed_at=time.time(),
        )
        sessions = run.get("sessions", [])
        sessions.append(
            {
                "start_step": starting_step,
                "end_step": step,
                "resources": run["resources"],
                "benchmark": run["benchmark"],
            }
        )
        run["sessions"] = sessions
        atomic_json(folder / "result.json", run)
        return run
    except BaseException as e:
        run.update(
            status="stopped"
            if isinstance(e, (BudgetExceeded, KeyboardInterrupt))
            else "failed",
            error=f"{type(e).__name__}: {e}",
            steps=step,
            history=history,
            resources=monitor.metrics(),
            stopped_at=time.time(),
        )
        atomic_json(folder / "result.json", run)
        raise


def infer_run(run_id, prompt, count=32, store=None):
    folder = Path(store or STORE) / "runs" / identifier(run_id)
    info, cp = verify_checkpoint(folder)
    torch.set_num_threads(2)
    model = Core(Config(**info["config"]))
    model.load_state_dict(load_file(str(cp / "model.safetensors")))
    tokenizer = Tokenizer.from_file(str(folder / "tokenizer.json"))
    ids = tokenizer.encode(prompt).ids or [0]
    output = model.generate(torch.tensor([ids]), count)[0].tolist()
    return {
        "text": tokenizer.decode(output, skip_special_tokens=False),
        "new_tokens": count,
        "model": run_id,
        "checkpoint_step": info["step"],
        "warning": "Research checkpoint; not instruction-tuned.",
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    new = sub.add_parser("create")
    new.add_argument("--dataset", required=True)
    new.add_argument("--profile", choices=PROFILES, default="tiny")
    new.add_argument("--steps", type=int, default=200)
    new.add_argument("--id")
    new.add_argument("--config")
    new.add_argument("--run", action="store_true")
    train = sub.add_parser("train")
    train.add_argument("run_id")
    train.add_argument("--resume", action="store_true")
    train.add_argument("--steps", type=int)
    infer = sub.add_parser("infer")
    infer.add_argument("run_id")
    infer.add_argument("prompt")
    infer.add_argument("--tokens", type=int, default=32)
    a = p.parse_args()
    if a.command == "create":
        config = (
            json.loads(Path(a.config).read_text()) if a.config else {"steps": a.steps}
        )
        result = create_run(a.dataset, a.profile, config, a.id)
        if a.run:
            result = train_run(result["id"])
    elif a.command == "train":
        result = train_run(a.run_id, resume=a.resume, additional_steps=a.steps)
    else:
        if not 1 <= a.tokens <= 128:
            p.error("tokens must be 1..128")
        result = infer_run(a.run_id, a.prompt, a.tokens)
    print(json.dumps(result, indent=2))
