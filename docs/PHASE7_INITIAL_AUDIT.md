# Phase 7 independent initial audit

2026-10-18 Asia/Karachi. Starting commit `d84d5c4` on `research/phase2-model-reliability`, clean tree. Remote SSH access succeeds and the remote research branch matches this commit; `main` is separate and will not be overwritten.

The actual baseline suite has **64 passing tests**, two more than Phase 6's earlier delivery report of 62. Existing source includes search providers (Wikipedia/arXiv/Crossref/GitHub), a Playwright page reader, extractive research/citation records, cowork SQLite chat and explicit workspace actions, rootless Python sandbox, independent Core training/checkpoints, local Ollama/LocalAI, isolated FCC and NVIDIA NIM adapters. Preserve these rather than building substitutes.

Phase 6's research pipeline is source-backed extraction, not a model-composed reasoned answer. It has unit tests and prior live evidence; the new live audit is stored in `artifacts/phase7/initial-live.json`. It lacks a registered-repository coding agent, durable multi-step task lifecycle, a project knowledge base and a completion-only tool-training experiment. No Phase 6 claim of those components is accepted as completed.

The selected independent checkpoint remains `phase2-small-language`, 984,192 parameters; the later Phase 5 instruction pilot is separate and reportedly failed held-out instruction tests. Checkpoint files and tokenizer/dataset identity will be hashed before new training. No pretrained external model is renamed Core.

REA Codex configuration now uses the verified NEXORA wrapper in this project, with a hash-named backup of the prior Netmirror registration. A fresh standalone MCP connection returned all 207 tools and Hopper available. The generic REA doctor flags its custom wrapper as configuration drift because it expects its raw generated command; functional MCP verification passes. Existing Codex connections require restart to pick up the changed registration.

The previously approved NVIDIA 4B GGUF download failed during a DNS outage, leaving resumable parts. It is being resumed for storage only. No successful full download or inference is assumed. The two models actually listed on NVIDIA's OpenAI publisher page are GPT-OSS-20B and Whisper Large V3; one is text reasoning/chat and the other speech recognition. Hosted inference requires account credentials; no paid request is authorized and local installation of those large weights is not assumed feasible on this laptop.
