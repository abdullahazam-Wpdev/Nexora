# Phase 4 verification — required acceptance tests

Run 2026-10-18 against `research/phase2-model-reliability`
(`HEAD` before this pass: `11d09fb`). Every row is an actual result from this
session, not an assumed pass. "Blocked"/"Skipped" rows name the precise
reason, per this project's own policy of never marking something passed
without evidence.

| # | Test | Result | Evidence / reason |
| --- | --- | --- | --- |
| 1 | Existing NEXORA Core checkpoint loading | **Pass** | Part of the full `pytest` run below (`tests/test_core.py`, `tests/test_phase3.py`) |
| 2 | Existing training and evaluation tests | **Pass** | Same run: `tests/test_research.py`, `tests/test_architecture_v2.py` |
| 3 | NVIDIA NIM API authentication when credentials are available | **Blocked** | No `NVIDIA_NIM_API_KEY` is configured anywhere in this environment. Obtain one at https://build.nvidia.com -- see [NVIDIA_NIM.md](NVIDIA_NIM.md) |
| 4 | NVIDIA model discovery | **Pass -- live, no key needed** | `GET /v1/models` is NVIDIA's public catalog endpoint. `GET /api/nvidia/status` was called live against the real `https://integrate.api.nvidia.com` from this session and returned `reachable: true, model_count: 81` with zero configuration |
| 5 | NVIDIA text generation | **Blocked** | Needs `NVIDIA_NIM_API_KEY`; confirmed live that `POST /v1/chat/completions` returns `401` without one. Request/response handling for this path is covered by mocked unit tests only |
| 6 | NVIDIA streaming | **Blocked** | Same reason as #5; SSE parsing is unit-tested against a mocked stream only |
| 7 | LocalAI generation | **Skipped this session** | Not re-started/re-exercised live to avoid adding memory pressure on a machine that had under 1 GiB RAM available at session start (see [HARDWARE_ROADMAP.md](HARDWARE_ROADMAP.md)). Prior verified evidence: `docs/cowork-delivery.md`, `docs/localai-inference.json` |
| 8 | Free Claude Code proxy startup if installed | **Skipped this session** | `scripts/fcc.sh start` was not re-run (same memory-pressure reason, plus this session's shell has no direct `systemctl`; it would route through `flatpak-spawn --host`, unverified non-interactively this session). Prior verified evidence: `docs/fcc-inference.json`, `docs/free-claude-code-rea-evidence.json` |
| 9 | Free Claude Code provider routing | **Skipped this session** | Same as #8 |
| 10 | NEXORA model switching | **Pass** | Live-checked this session: `GET /api/cowork/providers` returns `nvidia-nim` alongside the existing 10 providers; `GET /api/nvidia/status` responds correctly with no key configured |
| 11 | Real chat responses | **Pass** | `tests/test_cowork.py`, `tests/test_reference.py` in the full run |
| 12 | Coding-agent tool execution | **Partially verified** | `/write`/`/read` boundary and persistence tests pass (`tests/test_cowork.py`). The `/run` Podman sandbox itself was **not** re-exercised live this session: this session's shell runs inside a Flatpak sandbox where `podman`/`docker` are not directly on `PATH` (consistent with `docs/hardware-report.md`'s documented execution environment). Prior verified evidence: `docs/cowork-sandbox-results.json` (exit 0, non-root uid, network blocked, write blocked, time-limit enforcement all previously demonstrated) |
| 13 | MCP integration | **Pass** | `tests/test_cowork.py::test_real_stdio_mcp` actually launches `python -m nexora.cowork_mcp` as a subprocess and exercises it over real stdio; included in the passing run |
| 14 | Skill execution | **Structurally verified, not runtime-tested** | The two new skill files (`nexora-nvidia-nim`, `nexora-rea`) follow the existing frontmatter/content convention used by all other skills in `.agents/skills/`. Skills are instructions for an agent, not executable code, so "execution" here means an agent correctly loading and following them -- not independently re-verified by an automated test, same as the pre-existing skills |
| 15 | Database persistence | **Pass** | `tests/test_api.py` (memory + audit log round trip) in the full run |
| 16 | Model-training continuity | **Pass** | `tests/test_phase3.py` (exact-resume, checkpoint fork) in the full run |
| 17 | Resource limits | **Partially verified** | Bounded `Field(...)` input limits on the new NVIDIA endpoints are unit-tested (oversized `messages` list rejected with 422). The Podman cgroup limits (RAM/CPU/time) were not re-exercised live this session for the same sandbox-visibility reason as #12 |
| 18 | GitHub push if authorized | **Blocked** | See "GitHub push" below -- network reachability to GitHub is confirmed, but no push credential is configured |

## Full automated test run

```
46 passed in 9.51s   (.venv/bin/python -m pytest -q)
```

37 pre-existing tests (unchanged) + 9 new tests added this pass
(`tests/test_nvidia_nim.py`). `ruff check` passes on all new/changed files.
Separately, outside the automated suite, the real `nexora.nvidia_nim`
adapter was exercised live against `https://integrate.api.nvidia.com` (see
#4 above) -- a genuine network call, not a mock.

## GitHub push — exact blocker and how to unblock it

- `git remote -v` already points at
  `https://github.com/abdullahazam-Wpdev/Nexora.git`.
- Network: confirmed reachable this session (`curl https://api.github.com/zen`
  succeeded; raw TCP to `github.com:443` and `:22` both succeeded). An
  earlier, unrelated finding -- that this sandbox's default network is
  heavily restricted to an allowlist (NVIDIA's docs site is unreachable by
  direct HTTP from here; only the assistant's own separate web-fetch tooling
  could reach it for research) -- does **not** apply to GitHub.
- Credentials: none available. `gh` is not installed; the pre-staged
  `.tools/github-cli/gh.tar.gz` (GitHub CLI 2.102.0) is **corrupted/truncated**
  and cannot be extracted (`tar`/`gzip` report unexpected EOF), so it was not
  used. Running `sudo dnf install -y gh` was not attempted: it requires a
  sudo password this session cannot supply and is a system-wide change,
  which this project's own policy requires your explicit approval for
  regardless. No `GITHUB_TOKEN`/`GH_TOKEN` env var, no git credential helper,
  and no stored `gh` auth were found. An existing local SSH key
  (`~/.ssh/id_ed25519`, comment `abdullah-fedora-vps`) is present but is
  **not** registered with any GitHub account (`ssh -T git@github.com` ->
  `Permission denied (publickey)`).

**To unblock, pick one and tell me:**
1. Add this machine's public key to your GitHub account (Settings → SSH and
   GPG keys → New SSH key), then tell me to proceed. The key to paste is in
   `~/.ssh/id_ed25519.pub` (ends in `abdullah-fedora-vps`). I will then switch
   the remote to SSH and push.
2. Generate a GitHub Personal Access Token (repo scope) at
   https://github.com/settings/tokens and give it to me for this push only
   (I will not store or echo it; used once via a scoped git credential and
   discarded).
3. Run `gh auth login` yourself in your own interactive terminal (it needs a
   browser), then tell me it's done -- I can then push using the resulting
   credential helper.

All verified work from this pass is committed locally on
`research/phase2-model-reliability` and ready to push as soon as one of the
above is in place.
