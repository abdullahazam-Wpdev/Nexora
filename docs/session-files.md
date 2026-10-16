# Session deliverables

- `nexora/`: model, tokenizer/training/inference, dataset validation, configuration, FastAPI application.
- `frontend/`: Next.js / React / TypeScript application, responsive styles, package lock and build configuration.
- `migrations/001_initial.sql`: operational SQLite project/memory/audit/dataset schema.
- `tests/`: eight model, training, ingestion and API tests.
- `scripts/`: bootstrap, production startup, verification and browser QA.
- `compose.yaml`, `.env.example`: optional localhost-only PostgreSQL/Redis infrastructure.
- `pyproject.toml`, `requirements.lock`: reproducible Python setup.
- `README.md`, `docs/`: setup, hardware, decisions, architecture, roadmap, integration registry, verification, installed versions and browser/model evidence.
- Local ignored outputs: `.venv/`, `.tools/`, `frontend/node_modules/`, `frontend/.next/`, `artifacts/` (actual trained tokenizer/weights/resume state/SQLite/metrics).

Repository was created in the user-provided current workspace `/home/abdullah/Downloads/nexora-ai-os` rather than silently relocating it to the different path in the pasted requirements.
