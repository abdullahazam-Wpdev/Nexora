# Local knowledge base / RAG — Phase 6 (not started this pass)

Phase 6 §10 asks for a retrieval-augmented generation system: versioned
document ingestion (PDF/Markdown/text/HTML/papers/code/user documents),
full-text and optional vector search, content hashing, dedup, provenance --
independent of model weight training.

## Status: not implemented this pass

This pass's effort went to the search/browser/research vertical slice
(Milestones A-C), per Phase 6's own instruction to finish one working
vertical slice before expanding rather than starting every subsystem at
once. A real local knowledge base is a genuinely separate piece of
infrastructure (an ingestion pipeline, a storage/index layer, and a query
layer), and this project's own evidence from `docs/DATASET_MANIFEST.md`
shows that doing ingestion/provenance/dedup properly takes real,
unhurried engineering -- building it shallowly in the remaining time of
this pass would produce exactly the kind of untrustworthy shortcut this
project's rules forbid.

## What already exists and is directly reusable

- `nexora.data_engine.load_dataset` already implements hash-pinned,
  provenance-tracked, deduplicated document storage -- the same
  conventions a document knowledge base would need, just scoped to
  training datasets today.
- `artifacts/research-evidence/*.json` (new this pass, see
  `docs/RESEARCH_AGENT.md`) is already a versioned, hashed, timestamped
  store of retrieved web content -- a RAG index's ingestion log could be
  built as a natural extension of this rather than a new design.
- SQLite is already the project's metadata store (`nexora/api.py`'s
  `db()` context manager); a full-text index (SQLite FTS5, already
  bundled with Python's `sqlite3`) is the lightest-weight real next step,
  matching Phase 6's own instruction to "use a lightweight local
  retrieval implementation first" and "not download a large embedding
  model unless needed and approved."

## Concrete next step, scoped for a future pass

1. A `knowledge_documents` SQLite table (source, license/provenance,
   content hash, ingestion timestamp, version) plus an FTS5 virtual table
   for full-text query -- no new dependency, no download.
2. An ingestion endpoint accepting Markdown/text first (PDF/HTML parsing
   is more library-dependent and should follow once the core table/query
   path is proven).
3. Vector search only if FTS5 proves insufficient for a real query
   workload -- not pre-emptively, per Phase 6's own instruction.
