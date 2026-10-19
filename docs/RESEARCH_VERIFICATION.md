# Research and answer verification

Real run: keyless GitHub repository search for `fastapi in:name language:Python`,
rank/deduplicate URLs, read top3 in fresh isolated Chromium, extract text, hash evidence,
produce extractive cited answer, validate literal support. Status answered_with_evidence;
three sources read, 3/3 extracts supported,
zero failed reads; runtime11.50s. Public evidence records URLs/hashes;
full excerpts remain private under artifacts/research-evidence/16070e9d608fb32e.json.
This is successful research plumbing, not proof of a semantically correct synthesized answer.

Canonical dedup removes fragment/tracking parameters; ranking uses query-term overlap.
Publication metadata is labeled unverified or unknown. Page URL after redirect is retained.
Browser validates public navigation, blocks active scripts/subresources, uses no personal
profile and treats page text as untrusted. No content may approve tools or change policy.
Source conflicts require review; automatic semantic fact-conflict resolution is not implemented.

`/api/answers/verify` rejects missing citation IDs, changed evidence hashes and claims
not present in cited text. A caller can supply forged evidence; this endpoint is not a
source-authentication mechanism. Supported text may itself be false or an instruction;
matching does not authorize execution. No arbitrary prose entailment claim.
Deterministic evaluation: 20/20, unsupported accepts
0, supported rejections0.
This is a literal gate's fixture rate, **not a model hallucination rate or citation truth rate**.
No proprietary services or private chats were scraped for training.
