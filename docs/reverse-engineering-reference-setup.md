# REA, Hopper and local model reference setup

Research date: 2026-10-18. This work adds research tooling and a reference-model
adapter. It does not replace NEXORA Core or change its selected checkpoint.

## Repository review

The source snapshots are in ignored `artifacts/vendor-src/`. They are reference
copies, not vendored NEXORA application dependencies.

| Project | Reviewed commit | License | Role |
| --- | --- | --- | --- |
| [REA](https://github.com/morluto/rea) | `c12d9eda87aa5a022ee7e18ea96d8d03bfd12e96` | MIT | CLI/MCP analysis coordinator |
| [Awesome Reverse Engineering](https://github.com/morluto/awesome-reverse-engineering) | `29449628ed591065973ab8919a6df51ba254da82` | CC0-1.0 | Curated catalog; individual tools retain their licenses |

This is a scoped source and installation review, not an exhaustive security audit
of REA's full codebase or of every catalog entry. The pasted GitHub pages were
treated as background material; live source, package metadata and local behavior
were checked separately.

The reviewed Git snapshot and installed npm release are separate artifacts;
no reproducible-build equivalence attestation was performed. The npm lock pins
release package integrity.

The inspected REA paths establish this architecture:

- `src/main.ts` parses environment configuration, creates a binary session and
  starts the MCP stdio transport. CLI and MCP share session/provider composition.
- `src/composition/binary.ts` wires Hopper, Ghidra, IDA and Kuna as native
  providers, with separate auxiliary providers for portable artifact operations.
- `src/application/binary/BinarySessionComposition.ts` connects routing to an
  investigation record store. A provider candidate is not proof it is installed
  or that any target was analyzed.
- `src/main/transport.ts` loads optional providers independently and reports their
  failures rather than making all unrelated operations unavailable.
- `src/server/toolResult.ts` encodes evidence, budgets transport output and
  exposes retained evidence references for follow-up queries.
- `src/hopper/protocol.ts` validates bridge responses and progress messages.
  Hopper is the separate executable performing native analysis; REA is its
  orchestration layer.
- `src/application/LinuxHopper.ts`, `HopperReleaseFeed.ts`,
  `LinuxHopperPublisher.ts`, `HopperDownload.ts` and
  `src/process/DetachedPgpSignature.ts` disclose installation effects, restrict
  vendor origins, bound downloads and verify package/publisher identity.
- `SECURITY.md` describes local bridge authentication and explicitly states
  that analysis engines are not sandboxes.

The awesome catalog groups learning, file triage, native analysis, debugging,
managed/mobile, browser, firmware and related tools. Installing every entry
would include commercial, Windows/macOS-only and unrelated tooling. Those
entries are not required dependencies of either REA or NEXORA.

## Installed REA and evidence

REA 6.7.0 is installed under `.tools/rea`, with its npm dependency lock retained
under `tooling/rea/`. Node 22.23.3 satisfies its declared runtime range.
Installation uses `--ignore-scripts`; static JavaScript, Go metadata and a
Hopper native smoke target have been tested. Other optional providers and
native add-ons have not been exhaustively exercised.

```sh
./scripts/install-rea.sh
./scripts/rea.sh --version
./scripts/rea.sh inspect-go-binary /absolute/path/to/owned/binary --json
```

The existing connected MCP server advertises REA 6.7.0, skill version 42 and 207
tools. It is launched from a different pre-existing workspace. Its functional
registration was preserved. The new project CLI does not silently replace that
global registration. A read-only Codex setup plan is retained in
`artifacts/rea-setup-plan.json`; applying it would update
`/home/abdullah/.codex/config.toml` and create a recovery backup. That change
was not required for the connected tools and was not applied.

Static JavaScript smoke evidence:
`ev_f56a3d45daf6fdda49f9dc39f3cb54249b3edefb340207d7b09abb431ef75f19`
in `artifacts/rea-smoke-evidence.json`. The input is an explicitly generated,
two-file smoke fixture, not a reverse-engineered third-party platform. It was
parsed as inert text; no application code was executed.

The first downloaded upstream Ollama executable was inspected with REA's
built-in Go metadata reader. Evidence
`ev_19fd232021cfb77b8eac5f95de24bb7cdc70df0895346e1f278c577a0d4ca5b1`
is in `artifacts/rea-ollama-go-evidence.json`: 29,963,536 bytes, SHA-256
`8b4e471bcfc99125ae028b3b05938071999f8fddbebb30027f073460c5cb02e8`,
Go 1.26.0, embedded main module `github.com/ollama/ollama` with version `(devel)`.
The CLI version reports 0.40.6. Embedded metadata alone does not authenticate a
publisher, establish source equivalence or recover original source code. The
upstream archive remains incomplete until its full pinned checksum verifies.

## Hopper

[Hopper's official download page](https://www.hopperapp.com/download.html)
describes its commercial license and free demo: 30-minute sessions, no
save/export, and no debugger backend. The user explicitly approved the free
demo and license acceptance, with no purchase. Fedora's RPM release is
6.6.0 and 32,261,798 bytes. `scripts/verify-hopper.mjs` requires the reviewed
release metadata, archive length/checksum and detached signature under primary
key `7C2D73BAFAF5B9A710A69DA1A26DF815099B1BCD` before extraction.

The RPM transfer repeatedly stalled, so the official 29,393,252-byte Arch
archive was used for user-local extraction on Fedora. Its detached signature
verified under the pinned primary key; its signing subkey is
`868AD58E3275680D224CC9EC36D2884BC4DB1C33`, archive SHA-256
`609ff72b8caaf6e17c8c87c514b5d3b41e1040ddb9d48a14d4ba573d65c9aedb`.
The extracted executable matches vendor SHA-256
`b2271008fb82bf14cfae5c3644cdde2b11fc6804bd7c99d67032ec1b1942d53c`.
No Arch package-manager scripts were executed. Host Qt6/libbsd dependencies
were already present. The installation is `.tools/hopper/opt/hopper`, with a
user-local discovery symlink at `~/.local/share/rea/hopper`.

REA's demo helper also needed Xvfb. Fedora's signed
`xorg-x11-server-Xvfb-21.1.24-1.fc44.x86_64.rpm` (899,122 bytes) was extracted
under `.tools/xvfb`. The pinned helper patch in `scripts/patch-rea-xvfb.py`
changes only its default Xvfb path, after checking the original helper SHA-256
`ea5a3cab38843fc5405695de12ae2f711f1d2065ab347096624aab0d6f45e836`.
The reviewed public release metadata/key are retained under `tooling/hopper/`
for reproducible offline signature checks. `scripts/cache-hopper.mjs` uses REA's publisher API to reverify the signed
archive and retain complete package/key evidence for offline launch checks;
it does not disable publisher verification. `scripts/rea.sh` runs the CLI on
the Fedora host through `flatpak-spawn` so host Qt/glibc/xauth are available.

Native smoke analysis succeeded on a small, locally compiled C fixture with
`square` and `main`. Evidence
`ev_88c2b5056ad3b8da68b546765f754969d28c147578899ab8ce097c92c6f98d3c`
is saved in `artifacts/rea-hopper-smoke-host.json`. This verifies the CLI/native
provider path, not arbitrary third-party applications. CLI sessions clean up
their owned analysis processes when they exit. The follow-up function evidence
`ev_d3da02b373e5e06371ec8b1530d8e6f352dbd114db54d570896ae6ead82473d3`
records `square` at `0x1129`, pseudocode `rax = arg0 * arg0; return rax;`,
an `imul` instruction and a call from `main`. The fixture was built with
`cc -O0 -g`; it is a small test with debug symbols. Hopper reports that its
public API does not expose complete function-body ranges.


```sh
./scripts/install-hopper.sh
./scripts/hopper.sh  # Open the vendor GUI; choose its free demo mode
./scripts/rea.sh analyze /absolute/path/to/owned/binary --provider hopper --json
```

The project wrapper also has a separate stdio MCP verification script,
`scripts/verify_rea_mcp.mjs`; it does not edit client registration. An optional
configuration proposal is retained in `artifacts/rea-codex-wrapper-proposal.json`
with exact paths and a content-addressed backup plan. It has not been applied.

The already-running MCP server uses another installation and remains unchanged;
its native provider does not inherit this project's helper patch. Use the
project CLI for verified Hopper access. A future switch of the global MCP
registration to this wrapper requires a reviewed configuration change and a
client restart. Ghidra/Java, IDA, Kuna, Android and firmware engines are optional
and were not installed merely to clear diagnostic warnings.

## Ollama and reference model boundaries

The laptop has about 7.5 GiB RAM, with 1.1 GiB available at the initial check and
substantial swap already in use. CPU execution is selected. Rootless Podman
already works through `scripts/host-podman.sh`; Docker is not needed to run a
second container stack.

The upstream Ollama 0.40.6 Linux archive is 1,438,364,593 bytes, mostly unnecessary
GPU components for this machine. Its download timed out; temporary partial archive pieces were removed after the signed Fedora
installation succeeded. It is not the active runtime.
`scripts/install-ollama.sh` installs Fedora 44's maintained
`ollama-0.12.11-4.fc44.x86_64.rpm` (54,582,542 bytes) instead, by local extraction
under `.tools/ollama-fedora`. Its SHA-256 is
`f56508d8870255eae71b47f0cba6afa3cc5151457c79234503cbcecc8bb23f1c`.
Fedora package signature and header/payload digests passed under installed
trusted key fingerprint `36f612dcf27f7d1a48a835e4dbfcf71c6d9f90a6`.
The API/CLI version string is `0.0.0` in this distribution build; use the signed
RPM identity to track its upstream 0.12.11 source version. It is older than the
current upstream release. Do not use its string as an upgrade/version check.

The selected external reference is [SmolLM2 135M instruct Q4_K_M](https://ollama.com/library/smollm2:135m-instruct-q4_K_M),
an Apache-2.0 model published by Hugging Face. Its model tensor layer is
105,454,144 bytes. The pinned manifest SHA-256 is
`fd316850965252d917ac2bf811adef10ba91e129e5f2809f2a24a8501ff73e4f`;
the tensor blob SHA-256 is
`8030f04528538d47bda434f6f0bdf3952c40a58123e4d5e755332f23731a8684`.
The registry manifest is `artifacts/smollm2-135m-q4-manifest.json`.
This model is not an independently trained NEXORA checkpoint.

The larger F16 variant was attempted first. The old downloader retried a stalled
chunk and reset its progress. A manual extent-recovery attempt was interrupted
by an early runtime restart; cleanup discarded temporary model bytes. No Core
checkpoints or datasets were affected. The final workflow stages bounded,
resumable ranges outside Ollama's cache and verifies the complete published
SHA-256 before atomically publishing the blob. Quantization also reduces this
laptop's memory/storage requirements. The runtime is configured not to prune
unreferenced blobs at startup, so a verified blob survives manifest registration.

```sh
./scripts/prepare-reference.sh  # Stages/verifies weights and registers the model
./scripts/ollama.sh list
./scripts/ollama.sh status
./scripts/ollama.sh stop
./scripts/ollama.sh start
```

The start command uses a user systemd service with a 900 MiB memory maximum,
no service swap, 200% CPU quota, one loaded model and one parallel request.
It binds `127.0.0.1:11434` and stores models in
`artifacts/reference-models/ollama`. The unit is transient: restart it with the
script after logout/reboot. Model files persist. No privileged system service,
driver installation, paid provisioning or public listener is needed.

The Fedora build predates the current upstream cloud-disable flag. The script
sets that flag for a later compatible upgrade; this does not prove this build
enforces it. NEXORA uses only the pinned installed local model. No commercial
API or cloud model was configured or tested.

The NEXORA adapter exposes:

```sh
curl -f http://127.0.0.1:8000/api/reference/status
curl -f http://127.0.0.1:8000/api/reference/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Say hello in one sentence.","max_tokens":32}'
```

It verifies the installed model digest, limits inputs to 1,500 characters and
outputs to 128 tokens, fixes a 512-token context and two inference threads,
serializes requests within the single API process and requests immediate model
unloading. Its HTTP destination is fixed, proxy use is disabled, responses are
bounded to 1 MiB and local origin/host guards apply. Outputs identify their
external origin. Only model/token-count audit metadata is stored; the adapter
does not automatically retain prompts or answers as training data. Run NEXORA's
existing single-worker API configuration; the Python lock is process-local.

## What this enables next

Open source code and published model weights can be studied, reproduced under
their licenses, or used as explicitly labeled references. Disassembling a
client or observing a website cannot recover a remote service's foundation
model weights. Access to a UI also does not establish training rights.

The initial three-prompt smoke comparison is recorded below. The next research
step is a larger, fixed, executable task suite with a quality threshold before
selecting any teacher. A later
distillation experiment needs separately approved teacher-output provenance,
license/terms review, deduplication, contamination checks and a fixed held-out
suite. Teacher-generated training data must be labeled synthetic and reported
separately from the human-authored Phase 3 corpus. No such training is claimed
here, and SmolLM2 quality is not established merely by installing it.

Google Drive and personal Chrome pages were not needed for this local setup.
No account data was uploaded, synced or used as a training corpus.

## Final verification and observed limits

The canonical 105,454,144-byte quantized tensor blob matched its published
SHA-256. Its private staged download completed in 320.53 seconds. Ollama then
verified layer hashes, retained the Apache-2.0 notice and wrote the expected
model manifest. `GET /api/reference/status` reports `installed: true` with the
pinned digest. `artifacts/reference-download.json` records the transfer, and
`artifacts/reference-registration.log` records registration.

Real inference used CPU, two threads, a 512-token context and a maximum of 24
new tokens for each of three paired prompts. These are smoke probes, not a
capability benchmark or a matched-training comparison. The external model's
pretraining budget differs from Core's and was not reproduced here.

| Prompt | External SmolLM2 observation | Core observation | Reference end-to-end seconds | Reference decode tokens/s |
| --- | --- | --- | --- | --- |
| Say hello in one sentence. | Coherent sentence offering help, without saying hello | Python-tutorial fragment | 1.281 | 114.92 |
| What is 2 + 3? | Incorrect arithmetic-progression framing; no correct result within cap | Answer starts with 7, then repeated digits | 0.805 | 121.96 |
| Return only the word blue. | Noncompliant assistant boilerplate | Python-tutorial fragment | 0.735 | 127.10 |

Decode throughput excludes model loading and prompt processing; end-to-end
time includes them. Loads took 0.396–0.917 seconds. Service cgroup peak memory
was 341,487,616 bytes (325.67 MiB), including its processes and charged cache;
this is not whole-system peak RAM. The verified service limits are 943,718,400
bytes RAM, zero swap and 200% CPU quota. Raw outputs and timing fields are in
`artifacts/reference-verification/generation-smoke.json`, with resource readings
in `resources.txt` in the same directory.

API subprocess restart preserved reference availability. A separate Ollama
stop/start also preserved the model, followed by a successful real eight-token
generation through port 8000: `Hello! I'm here to help with`. The model unloads
after each request. Evidence is in
`artifacts/reference-verification/verification.json` and
`after-runtime-restart.json`.

Core remains `phase2-small-language`, step 400, engine version 2. Its bundle
passes hash, tokenizer, tensor-shape and finiteness checks. The model tensor
SHA-256 remains
`0b10d349fe2a8517544cd31cee03140eba7aa730fd1087ae01f0b02b1b56ee84`;
the selected-model manifest SHA-256 is unchanged at
`1b8e5d922546dd0170ee4e2b51395eb7fecffc3d70d66aa80e79cdc3935352c1`.
Its checkpoint remains
`artifacts/runs/phase2-small-language/checkpoints/step-0000400/`.
No training, checkpoint promotion or synthetic dataset ingestion was performed.

Validation: all 33 Python tests pass, Ruff `F` checks pass, Python dependency
consistency passes, shell syntax checks pass, frontend type checking and its
production build pass. The REA npm dependency audit reports zero known
vulnerabilities at the time of this check. This does not establish absence of
unknown vulnerabilities or that every optional REA engine works.

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check nexora tests scripts --select F
.venv/bin/python -m pip check
export PATH="$PWD/.tools/node/bin:$PATH"
npm --prefix frontend run typecheck
npm --prefix frontend run build
.tools/node/bin/node scripts/verify_rea_mcp.mjs
.venv/bin/python -m scripts.reference_qa
```

The NEXORA backend is running at `http://127.0.0.1:8000/docs`. Port 3000 belongs
to a separate FRAME application and was left untouched. The frontend build was
validated without redesigning or replacing that running application.

The tiny reference failed basic constrained prompts and is not approved as an
automatic training teacher. Larger-model inference, fine-tuning, teacher-data
generation, remote proprietary model replication and a capable general assistant
have not been demonstrated by this installation.

## Changed files

- `README.md`
- `docs/installed-versions.json`
- `docs/integrations.md`
- `docs/reverse-engineering-reference-setup.md`
- `docs/roadmap.md`
- `nexora/api.py`
- `nexora/reference.py`
- `scripts/cache-hopper.mjs`
- `scripts/download_reference.py`
- `scripts/hopper.sh`
- `scripts/install-hopper.sh`
- `scripts/install-ollama.sh`
- `scripts/install-rea.sh`
- `scripts/ollama.sh`
- `scripts/patch-rea-xvfb.py`
- `scripts/prepare-reference.sh`
- `scripts/rea.sh`
- `scripts/reference_qa.py`
- `scripts/verify-hopper.mjs`
- `scripts/verify_rea_mcp.mjs`
- `tests/test_reference.py`
- `tooling/hopper/hopper-public-key.asc`
- `tooling/hopper/releases-6.6.0.json`
- `tooling/rea/package-lock.json`
- `tooling/rea/package.json`
- `tooling/reference/smollm2-135m-q4_K_M.manifest.json`
