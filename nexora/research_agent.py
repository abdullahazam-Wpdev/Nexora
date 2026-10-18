"""Evidence-based research agent: question -> search -> read -> cite -> answer.

This is Phase 6's research pipeline. It does NOT generate a model-written
prose answer yet (no capable local model exists to draft one honestly --
see docs/AGENT_EVALUATION.md); it does the verifiable half of the pipeline
for real: live search, live page reading, evidence recording with content
hashes and retrieval timestamps, and a citation list. The "answer" field is
an extractive summary built only from retrieved snippets/excerpts, never
from model invention, and is labeled as such.

Evidence store: artifacts/research-evidence/<id>.json, one file per
research call, each citation traceable to an actual retrieved source.
Page/search content is treated as untrusted data throughout -- never
executed, never treated as instructions to this agent.
"""

import hashlib
import json
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nexora.browser_reader import read_url
from nexora.config import STORE
from nexora.search import PROVIDERS
from nexora.search import search as run_search

MAX_SOURCES_TO_READ = 3


def research(question, providers=None, read_top=True):
    """Run the real pipeline. Returns a dict with citations and status --
    never fabricates a URL, snippet or page excerpt. If search itself is
    unavailable, that is reported explicitly, not papered over."""
    started = time.monotonic()
    search_result = run_search(question, providers, limit=5)
    citations = []
    read_errors = {}
    if not search_result["results"]:
        return {
            "question": question,
            "status": "no_sources_found",
            "detail": "Live search returned no results for this query"
            + (f" ({search_result['errors']})" if search_result["errors"] else "."),
            "citations": [],
            "answer": None,
            "search_errors": search_result["errors"],
            "seconds": time.monotonic() - started,
        }
    for i, item in enumerate(search_result["results"][:MAX_SOURCES_TO_READ]):
        citation = {
            "citation_id": f"c{i + 1}",
            "title": item["title"],
            "url": item["url"],
            "publisher": item["publisher"],
            "provider": item["provider"],
            "retrieved_at": item["retrieved_at"],
            "published_at": item.get("published_at"),
            "search_snippet": item["snippet"],
            "content_hash": item["content_hash"],
            "full_text_excerpt": None,
            "read_status": "not_attempted",
        }
        if read_top:
            try:
                page = read_url(item["url"])
                excerpt = page["text"][:1200]
                citation["full_text_excerpt"] = excerpt
                citation["read_status"] = "read"
                citation["content_hash"] = hashlib.sha256(
                    (item["url"] + excerpt).encode()
                ).hexdigest()
            except (ValueError, RuntimeError) as exc:
                citation["read_status"] = f"failed: {exc}"
                read_errors[item["url"]] = str(exc)
        citations.append(citation)

    # Extractive, non-invented summary: join the strongest excerpt from
    # each source. This is deliberately NOT a fluent model-written answer
    # -- no capable local model exists to draft one honestly yet. A future
    # pass can hand `citations` to a real model as grounding context once
    # one is available (see docs/RESEARCH_AGENT.md).
    pieces = []
    for c in citations:
        text = c["full_text_excerpt"] or c["search_snippet"]
        if text:
            pieces.append(f"[{c['citation_id']}] {text.strip()[:400]}")
    answer = "\n\n".join(pieces) if pieces else None

    record = {
        "question": question,
        "status": "answered_with_evidence" if answer else "sources_found_unreadable",
        "citations": citations,
        "answer": answer,
        "answer_kind": "extractive_summary_of_retrieved_sources,_not_model_generated_prose",
        "search_errors": search_result["errors"],
        "read_errors": read_errors,
        "seconds": time.monotonic() - started,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (STORE / "research-evidence").mkdir(exist_ok=True)
    stamp = hashlib.sha256((question + str(time.time())).encode()).hexdigest()[:16]
    (STORE / "research-evidence" / f"{stamp}.json").write_text(
        json.dumps(record, indent=2)
    )
    record["evidence_id"] = stamp
    return record


class ResearchRequest(BaseModel):
    question: str = Field(min_length=1, max_length=400)
    providers: list[str] | None = None
    read_top: bool = True


def router(audit):
    routes = APIRouter(prefix="/api/research", tags=["research agent"])

    @routes.post("/ask")
    def ask(body: ResearchRequest):
        if body.providers:
            unknown = set(body.providers) - set(PROVIDERS)
            if unknown:
                raise HTTPException(422, f"Unknown provider(s): {sorted(unknown)}")
        result = research(body.question, body.providers, body.read_top)
        audit(
            "research.ask",
            json.dumps(
                {
                    "question": body.question,
                    "status": result["status"],
                    "citation_count": len(result["citations"]),
                }
            ),
        )
        return result

    return routes
