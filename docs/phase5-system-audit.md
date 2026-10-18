# Phase 5 — independent system audit

Run 2026-10-18, this session, against `research/phase2-model-reliability` at
commit `db8fbb7` (pushed to `origin` and tracking it). Every number below is a
live measurement from this session, not a restated prior claim.

## 1-2. Git state and tests

```
On branch research/phase2-model-reliability
Your branch is up to date with 'origin/research/phase2-model-reliability'.
nothing to commit, working tree clean
```

Remote: `git@github.com:abdullahazam-Wpdev/Nexora.git`, authenticated via SSH
(confirmed working this session). `research/phase2-model-reliability` tracks
`origin/research/phase2-model-reliability`. `master` (local-only, never
pushed) sits at the original root commit `6d3b60f` and is stale; everything
since lives on the research branch.

```
.venv/bin/python -m pytest -q
46 passed in 10.36s
```

All pre-existing and Phase 4 tests still pass. No regressions.

## 3-6. Checkpoint, dataset, tokenizer, parameter count -- independently reproduced

The selected checkpoint is `phase2-small-language`
(`artifacts/selected-model.json`). Rather than trust `result.json`, this
session rebuilt the model from the checkpoint tensors and tokenizer and
re-ran evaluation from scratch:

| Check | Stored (result.json) | Freshly reproduced this session |
| --- | --- | --- |
| Parameter count | 984,192 | **984,192** (counted via `sum(p.numel() for p in model.parameters())` on a model rebuilt from `model.safetensors`) |
| Architecture | `dim=128, layers=4, heads=4, context=128, vocab_size=1024, tie_embeddings=True` | Same `Config`, used to reconstruct the model |
| Tokenizer | sha256-pinned in `tokens.json`/`latest.json` | `verify_checkpoint()` confirmed the live `tokenizer.json` hash still matches |
| Test loss | 4.1786155273320755 | **4.178615570217266** (same to 8 significant figures; the ~1e-8 difference is ordinary floating-point summation-order noise, not a discrepancy) |
| Test perplexity | 65.27541859339495 | **65.27542139274378** |
| Test tokens | 12,809 | 12,809 |
| Tied-embedding check | -- | `torch.equal(head.weight, embedding.weight)` holds |
| Finite weights | -- | All tensors finite (no NaN/Inf) |

This is a genuine, independent reproduction (fresh forward passes over the
test split, not a cached number), run via `nexora.research.verify_checkpoint`
+ `evaluate()`. Dataset: `python-tutorial-bd831076dc61` (PSF-2.0, human-
authored CPython 3.13 tutorial, approved, hash-pinned). Other recorded runs
(`phase3-baseline-s42/s43`, `phase3-compact-*`, `phase3-wider-*`,
`phase3-compatible-fork`, `localai-docs-pilot-8`) exist under
`artifacts/runs/` with their own manifests; they were not individually
re-run this pass, only the currently-selected checkpoint was.

## 7. Chat and coworker behavior -- live-exercised, not assumed

Through the real FastAPI app (`TestClient`, no mocking of the cowork layer):

- `GET /api/health` → `{"status": "ok", "memory_total": 8030420992,
  "memory_available": 972849152, "device": "CPU", "podman": "Host bridge
  available", ...}` -- the application's own health check independently
  agrees with the OS-level RAM measurement in §10.
- `POST /api/cowork/threads/.../messages` with `/write audit.txt` then
  `/read audit.txt` round-tripped correctly through the real sandboxed
  workspace tool.
- `GET /api/cowork/providers` lists all 11 registered providers including
  `nvidia-nim`.

## 8. LocalAI, Ollama, NVIDIA

- **Ollama**: running (`127.0.0.1:11434` open). `GET /api/reference/status`
  → `installed: true` for the pinned `smollm2:135m-instruct-q4_K_M`. Live and
  healthy.
- **LocalAI**: not running (`127.0.0.1:8080` refused). Not started this
  session to avoid adding load while other work was in flight; prior
  verified evidence stands in `docs/cowork-delivery.md`.
- **NVIDIA NIM**: re-confirmed live, no key, `GET /v1/models` →
  **81 real catalog models**, same result as the Phase 4 pass.

## 9. GitHub remote and tracking branch

Already covered in §1-2: SSH-authenticated, tracking branch set, working
tree clean, nothing unpushed.

## 10. Hardware -- the RAM discrepancy, resolved

```
free -h
               total        used        free      shared  buff/cache   available
Mem:           7.5Gi        6.5Gi       224Mi       425Mi       1.3-1.6Gi    1.0Gi
Swap:          7.5Gi        5.5Gi       2.0Gi
MemTotal:      7842208 kB   (7.48 GiB)
```

**This is the real, physical RAM of this machine -- not a sandbox artifact,
and not 32 GiB.** Evidence for that conclusion, checked specifically this
session:

- This shell runs inside the VS Code Flatpak sandbox
  (`FLATPAK_ID=com.visualstudio.code`, `/.flatpak-info` present,
  `container=flatpak`). Flatpak is a namespace/bind-mount sandbox that shares
  the host kernel -- it does **not** virtualize or report fake memory
  figures the way a VM or memory-cgroup-limited container would.
- No cgroup v2 memory ceiling is visible (`/sys/fs/cgroup/memory.max` does
  not exist in this view), so there is no artificial cap being hit; the
  kernel's own `/proc/meminfo` is what reports 7,842,208 kB total.
- The running NEXORA API's own `psutil`-based health check, from inside the
  Python process (not a shell command), independently reports the same
  figure (8,030,420,992 bytes = 7.48 GiB) -- two different measurement paths
  (kernel `/proc/meminfo` via shell, and `psutil.virtual_memory()` via
  Python) agree.
- This matches the prior phase's `docs/hardware-report.md` finding exactly,
  across three independent sessions now.

**Conclusion: treat 7.5 GiB total RAM, with typically under 1 GiB available,
as the real and current constraint for all Phase 5 work. Do not plan any
training or model-loading step around 32 GiB.** CPU: Intel Core i5-1135G7,
4 cores / 8 threads. GPU: Intel Iris Xe integrated only; no `nvidia-smi`, no
CUDA, no discrete GPU. Storage: 183 GiB free on `/home`.

## Unplanned finding: a live 2.8 GB download is in progress

While running this audit, `ps`/`pgrep` showed a background process (PID
27523, started independently of this session, not launched by this audit)
actively running `scripts/download-nvidia-reference.py` -- the storage-only
NVIDIA Nemotron-3-Nano-4B GGUF download flagged in the Phase 4 pass as
**not yet run, pending approval**. It has been running for roughly an hour
and is about 61% complete (1.7 of 2.78 GB) as of this audit. This session
did not start it and is not stopping it -- it was not launched by this audit
and appears to be separate, already-in-progress work, most likely started
directly by you. It downloads to disk only (per the script's own design:
`"purpose": "storage-only; not loaded or selected"`) and is not consuming
meaningful RAM (process RSS ~14 MB), so it does not change the RAM
constraint above. It is flagged here so it's not mistaken for something this
pass initiated, and as a reminder per `docs/HARDWARE_ROADMAP.md`: once
downloaded, loading a 4B-parameter model for actual inference is not
feasible on this machine's measured RAM.

## Net effect on Phase 5 planning

Every subsequent phase in this pass is scoped to the measured ~1 GiB
available RAM and 4-core CPU, not the originally assumed 32 GiB. That means:
no multi-GB model downloads beyond what's already in flight, no concurrent
heavy services, small bounded training pilots only, and explicit approval
requests before anything that would change that picture.
