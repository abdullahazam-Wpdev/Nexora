# Typed project memory

Conversation history remains in `cowork.sqlite3`. New `project-memory.sqlite3` stores owner-entered project notes, preferences, documents, evaluations and improvement proposals. Research evidence retains its own source URLs/hashes/timestamps; agent tasks retain their own execution history; datasets/checkpoints remain separate. None of these stores automatically feed training.

`/api/knowledge/entries` supports create, query, correction and deletion. Entries require provenance, a project namespace and 1–365 retention days (default 30). Content hashes deduplicate within kind/namespace. Retrieval is bounded to 20 matches and deletes expired entries. A namespace query never retrieves another namespace's notes. The UI Library offers local note storage, search and deletion; correction is available through PUT.

`/api/knowledge/skills?q=...` discovers and ranks matching project skills by lexical overlap, returning at most eight. This is a small lexical selector, not semantic retrieval or learned skill acquisition. Returned memory and Markdown are untrusted reference data and cannot authorize tools. Source-backed research and an owner note are not interchangeable truth claims. Private conversations, credentials and unrelated browser sessions are excluded from datasets and Git.
