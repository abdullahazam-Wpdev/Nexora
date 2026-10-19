# Retrieval and owner memory

Existing conversations, owner notes, task history, public research evidence and
training data remain separate. Owner notes support correction/deletion/expiry;
chat optionally uses three bounded project/preference notes. See
MEMORY_ARCHITECTURE.md. No transcript or memory automatically trains weights.

Phase 8 adds `documents.sqlite3` with a SQLite FTS5 inverted index. The Library
accepts owner-pasted title/text, at most 32,000 characters. The API also accepts
an HTTPS source citation or `urn:` project identifier; ingestion does not fetch
the URI or independently validate the publication. Documents are normalized
into 800-character chunks with a 700-character stride, text SHA-256, stable
`document-id:ordinal` citations and project namespace. Exact content deduplicates
within a project. Phrase terms are quoted for FTS, at most twelve query tokens;
search returns at most ten BM25-ranked chunks. This is lexical retrieval, not
vector similarity or a semantic fact-checker. Results carry untrusted-data flags.

`POST /api/documents` ingests; `GET /api/documents?project=local&q=...` searches;
`DELETE /api/documents/{id}?project=local` removes both document and index chunks.
The UI lists citations and deletion controls. Correct a document by deleting its
old version and ingesting the corrected text; owner note PUT remains supported.
Document search is manual/API-driven, not automatically injected into chat.

Three authored retrieval queries passed top-1 matching, exact excerpt checking
and namespace isolation. This tiny smoke set is not a broad retrieval benchmark.
Public-source research retains URL/title/retrieval times and excerpts; publication
dates are not reliably extracted, and independent semantic source agreement is
not automatically verified. The existing quotation verifier checks literal
inclusion only. No confidence score or guaranteed factual accuracy is claimed.
