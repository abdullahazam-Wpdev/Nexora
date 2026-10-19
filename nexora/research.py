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

ENGINE_VERSION = 3
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
    temperature_interval: float = 0.25
    min_battery_percent: float = 15
    eval_batch_size: int = 8
    architecture: dict | None = None
    tokenizer_run: str | None = None
    evaluate_test: bool = True

    def __post_init__(self):
        if not 0 <= self.min_battery_percent <= 50:
            raise ValueError("Invalid battery reserve")
        integer_fields = (
            "steps",
            "schedule_steps",
            "warmup_steps",
            "batch_size",
            "accumulation",
            "seed",
            "threads",
            "eval_every",
            "checkpoint_every",
            "vocab_size",
            "eval_batch_size",
            "max_rss_mb",
            "min_available_mb",
            "min_disk_mb",
        )
        if any(type(getattr(self, key)) is not int for key in integer_fields):
            raise ValueError("Discrete training configuration values must be integers")
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
            not 1 <= self.eval_batch_size <= 16
            or not 0 <= self.temperature_interval <= 2
        ):
            raise ValueError("Invalid evaluation or sensor polling configuration")
        if self.architecture is not None:
            if set(self.architecture) != {"dim", "layers", "heads", "context"}:
                raise ValueError("Architecture requires dim, layers, heads and context")
            if any(type(value) is not int for value in self.architecture.values()):
                raise ValueError("Architecture dimensions must be integers")
            shape = Config(
                vocab_size=self.vocab_size, **self.architecture, tie_embeddings=True
            )
            if (
                shape.dim > 256
                or shape.layers > 6
                or shape.heads > 16
                or not 16 <= shape.context <= 256
            ):
                raise ValueError("Architecture exceeds bounded CPU limits")
            if (
                13 * shape.dim**2 * shape.layers
                + shape.vocab_size * shape.dim
                + 2 * shape.dim * shape.layers
                + shape.dim
                > 5_000_000
            ):
                raise ValueError("Architecture exceeds CPU parameter budget")
        if self.tokenizer_run is not None:
            identifier(self.tokenizer_run)
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
        self._temperature_at = float("-inf")
        self._temperature = None
        self.sensor_reads = 0
        self.cpu_start = sum(self.process.cpu_times()[:2])

    def check(self):
        if self.cancel_path and self.cancel_path.exists():
            raise BudgetExceeded("Cancellation requested")
        rss = self.process.memory_info().rss
        self.peak_rss = max(self.peak_rss, rss)
        now = time.monotonic()
        if now - self._temperature_at >= self.c.temperature_interval:
            self._temperature = temperature()
            self._temperature_at = now
            self.sensor_reads += 1
            battery = psutil.sensors_battery()
            if (
                battery
                and not battery.power_plugged
                and battery.percent < self.c.min_battery_percent
            ):
                raise BudgetExceeded(
                    "Battery reserve floor reached; plug into AC before resuming"
                )
        temp = self._temperature
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
            "temperature_sensor_reads": self.sensor_reads,
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
    if c.tokenizer_run:
        reference = store / "runs" / c.tokenizer_run
        reference_info, _ = verify_checkpoint(reference)
        if reference_info["config"]["vocab_size"] != c.vocab_size:
            raise ValueError(
                "Frozen tokenizer vocabulary must match the run configuration"
            )
        reference_tokens = json.loads((reference / "tokens.json").read_text())
        if "evaluation_suite" in manifest:
            # Parent tokenizer must never have been trained on the frozen held-out sources.
            _, parent_docs = load_dataset(
                json.loads((reference / "result.json").read_text())["dataset_id"], store
            )
            _, candidate_docs = load_dataset(dataset_id, store)
            train_sources = {d["source_id"] for d in parent_docs["train"]}
            heldout_sources = {
                d["source_id"]
                for split in ("validation", "test")
                for d in candidate_docs[split]
            }
            if train_sources & heldout_sources:
                raise ValueError(
                    "Reference tokenizer training sources contaminate held-out evaluation"
                )
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
        "name": f"NEXORA Core {profile} / {manifest['name']}"
        if not c.architecture
        else f"NEXORA Core d{c.architecture['dim']}l{c.architecture['layers']} / {manifest['name']}",
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
        "architecture": c.architecture or PROFILES[profile],
        "tokenizer_reference": {
            "run": c.tokenizer_run,
            "sha256": reference_tokens["tokenizer_sha256"],
        }
        if c.tokenizer_run
        else None,
        "evaluation_suite": manifest.get("evaluation_suite"),
        "history": [],
        "steps": 0,
        "warning": "Independent next-token model; not instruction-tuned or a validated assistant.",
    }
    atomic_json(folder / "result.json", run)
    return run


def _prepare_tokens(folder, manifest, documents, c, monitor):
    started = time.monotonic()
    if c.tokenizer_run:
        reference = folder.parent / c.tokenizer_run
        expected = json.loads((folder / "result.json").read_text())[
            "tokenizer_reference"
        ]["sha256"]
        if sha256(reference / "tokenizer.json") != expected:
            raise ValueError("Frozen tokenizer changed")
        tokenizer = Tokenizer.from_file(str(reference / "tokenizer.json"))
    else:
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
def evaluate(model, tokens, context, monitor=None, batch_size=1):
    """Same disjoint windows/targets as v2, batched without padding or target omissions."""
    if len(tokens) < 2 or context < 1 or not 1 <= batch_size <= 16:
        raise ValueError("Invalid evaluation tokens, context or batch size")
    was_training = model.training
    model.eval()
    total = 0.0
    count = 0
    try:
        full = (len(tokens) - 1) // context
        for index in range(0, full, batch_size):
            if monitor:
                monitor.check()
            starts = [j * context for j in range(index, min(full, index + batch_size))]
            x = torch.from_numpy(
                np.stack([tokens[j : j + context] for j in starts]).astype(np.int64)
            )
            y = torch.from_numpy(
                np.stack([tokens[j + 1 : j + context + 1] for j in starts]).astype(
                    np.int64
                )
            )
            losses = F.cross_entropy(
                model(x).flatten(0, 1), y.flatten(), reduction="none"
            ).reshape(len(starts), context)
            # Preserve per-window FP32 reduction before Python float accumulation.
            for value in losses.sum(dim=1).tolist():
                if not math.isfinite(value):
                    raise ValueError("Nonfinite evaluation loss")
                total += value
            count += len(starts) * context
        start = full * context
        size = len(tokens) - 1 - start
        if size:
            if monitor:
                monitor.check()
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
    if info.get("engine_version") not in {2, ENGINE_VERSION}:
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


from nexora.compute_budget import compute_job


@compute_job('training')
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
            if run.get("migration") and not (folder / "latest.json").exists():
                import shutil

                migration = run["migration"]
                parent = store / "runs" / migration["parent_run"]
                info, original_cp = verify_checkpoint(parent, migration["checkpoint"])
                if (
                    sha256(original_cp / "resume.pt")
                    != migration["checkpoint"]["files"]["resume.pt"]
                ):
                    raise ValueError("Migration parent changed")
                for filename in (
                    "tokenizer.json",
                    "tokens.json",
                    "train.npy",
                    "validation.npy",
                    "test.npy",
                ):
                    shutil.copyfile(parent / filename, folder / filename)
                meta = json.loads((folder / "tokens.json").read_text())
                state = torch.load(
                    original_cp / "resume.pt", weights_only=True, map_location="cpu"
                )
                state["engine_version"] = ENGINE_VERSION
                state["code_sha256"] = run["code_sha256"]
                state["scheduler"]["config"] = run["training"]
                tokenizer = Tokenizer.from_file(str(folder / "tokenizer.json"))
                config = Config(**state["config"])
            else:
                info, cp = verify_checkpoint(folder)
                state = torch.load(
                    cp / "resume.pt", weights_only=True, map_location="cpu"
                )
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
                **run.get("architecture", PROFILES[run["profile"]]),
                tie_embeddings=True,
                init_std=0.02,
            )
        del documents
        if meta["dataset_version"] != manifest["version"]:
            raise ValueError("Token shards reference another dataset")
        if resume and (
            state["dataset_version"] != manifest["version"]
            or state["tokenizer_sha256"] != meta["tokenizer_sha256"]
        ):
            raise ValueError("Resumed checkpoint data/tokenizer identity mismatch")
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
                model, arrays["validation"], config.context, monitor, c.eval_batch_size
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
                    model,
                    arrays["validation"],
                    config.context,
                    monitor,
                    c.eval_batch_size,
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
        validation = evaluate(
            model, arrays["validation"], config.context, monitor, c.eval_batch_size
        )
        test = (
            evaluate(model, arrays["test"], config.context, monitor, c.eval_batch_size)
            if c.evaluate_test
            else None
        )
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
            test_loss=test["loss"] if test else None,
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


@compute_job("core inference")
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


def fork_checkpoint(parent_id, new_id=None, *, store=None):
    """Explicitly fork a verified v2/v3 checkpoint; preserve training state and source."""
    store = Path(store or STORE)
    parent = store / "runs" / identifier(parent_id)
    original = json.loads((parent / "result.json").read_text())
    info, checkpoint = verify_checkpoint(parent)
    if (
        original["engine_version"] not in {2, 3}
        or info["engine_version"] != original["engine_version"]
    ):
        raise ValueError(
            "Explicit migration accepts verified version-2/version-3 checkpoints only"
        )
    state = torch.load(checkpoint / "resume.pt", weights_only=True, map_location="cpu")
    if (
        state["config"] != info["config"]
        or state["dataset_version"] != original["dataset_version"]
        or state["tokenizer_sha256"] != info["tokenizer_sha256"]
    ):
        raise ValueError("Inconsistent version-2 checkpoint identities")
    if (
        state["scheduler"]["config"] != original["training"]
        or state["step"] != info["step"]
    ):
        raise ValueError("Inconsistent version-2 schedule")
    result = create_run(
        original["dataset_id"], original["profile"], original["training"], new_id, store
    )
    result["migration"] = {
        "parent_run": parent_id,
        "checkpoint": info,
        "from_engine": original["engine_version"],
        "parent_code_sha256": original["code_sha256"],
        "to_engine": 3,
        "policy": "Fork only; preserve data, tokenizer, model, optimizer, sampler and LR schedule. New monitoring/evaluation batching defaults are operational changes.",
    }
    result["architecture"] = {
        k: original["config"][k] for k in ("dim", "layers", "heads", "context")
    }
    atomic_json(store / "runs" / result["id"] / "result.json", result)
    return result


def migrate_v2_run(parent_id, new_id=None, *, store=None):
    """Version-specific compatibility entry point, retained for tested v2 migration."""
    root = Path(store or STORE)
    original = json.loads(
        (root / "runs" / identifier(parent_id) / "result.json").read_text()
    )
    if original["engine_version"] != 2:
        raise ValueError("Version-2 migration requires a version-2 parent")
    return fork_checkpoint(parent_id, new_id, store=store)
