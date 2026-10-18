# Agent capabilities — what NEXORA's coworker can actually do

Full evidence: [cowork-delivery.md](cowork-delivery.md); summary restated
here per Phase 4's request for a dedicated capabilities doc, re-verified
2026-10-18 (45/45 tests passing, including the 8 new NVIDIA NIM tests added
this pass).

## Implemented and verified

| Capability | Mechanism | Boundary |
| --- | --- | --- |
| Chat | Persistent SQLite-backed conversation (`artifacts/cowork.sqlite3`) | Survives API restarts; not auto-used as training data |
| File reading | `/read <path>` | Confined to `artifacts/coworkspace/` |
| Scoped file editing | `/write <path>` | Creates new files only; never overwrites existing work |
| Repository inspection | `/files` | Lists the isolated workspace, not the host filesystem |
| Code generation | Model-generated text saved via `/write` | Prose never silently becomes a command |
| Test/code execution | `/run <path>` | Rootless Podman, no network, read-only root + workspace, unprivileged user, dropped capabilities, 96 MiB RAM, 0.5 CPU, 32 processes, 10s wall clock |
| Research | `/catalog <query>` over attributed `public-apis`/`awesome-free-models` snapshots | Discovery only; entries are not auto-installed or license-approved |
| Document processing | Workspace MCP server (`workspace_list/read/create`, `catalog_search`) | stdio, local only |
| Tool execution | The above `/run` sandbox | No arbitrary host shell tool exists |
| Human approval | Every action above is explicit user input in chat, not autonomous | No standing permission to act without a new user message |

## Explicitly not implemented (do not claim otherwise)

- **Task planning**: no multi-step natural-language plan decomposition.
  Reliable autonomous planning remains research work per the README.
- **Task verification / multi-file repository editing**: not demonstrated;
  each action is one explicit command, not a reviewed edit-and-test loop.
- **Browser testing**: `scripts/browser_qa.py` / `scripts/cowork-browser-qa.py`
  exist and were used for this project's own QA, but there is no
  general-purpose browser-automation tool exposed to chat.
- **Autonomous agent creation**: skills in `.agents/skills/` are instructions
  for an agent, not something NEXORA Core learns or generates on its own.

## Backend used for agent workflows today

Per Phase 4 §9, "an available capable backend" for these workflows is
whichever chat provider is selected (Ollama/SmolLM2 or NEXORA Core today;
NVIDIA NIM once a key is configured and verified -- see
[NVIDIA_NIM.md](NVIDIA_NIM.md)). NEXORA Core itself remains a research
backend: it has not been shown to reliably perform tool calling, so it is
not relied on to drive the `/run`/`/write` actions above -- those are
deterministic chat commands parsed by the cowork layer, not model-initiated
tool calls.
