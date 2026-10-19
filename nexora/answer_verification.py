"""Conservative evidence checks. Text support is not independent factual truth."""

import hashlib, re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from fastapi import APIRouter
from pydantic import BaseModel, Field


def canonical_url(url):
    p = urlsplit(url)
    return urlunsplit(
        (
            p.scheme.lower(),
            p.netloc.lower(),
            p.path.rstrip("/") or "/",
            urlencode(
                [
                    (k, v)
                    for k, v in parse_qsl(p.query)
                    if not k.startswith("utm_") and k not in {"fbclid", "gclid"}
                ]
            ),
            "",
        )
    )


def ranked_sources(question, items):
    terms = set(re.findall(r"\w+", question.lower()))
    seen = set()
    rows = []
    for item in items:
        url = canonical_url(item["url"])
        if url in seen:
            continue
        seen.add(url)
        row = dict(item)
        row["canonical_url"] = url
        row["query_term_overlap"] = len(
            terms
            & set(re.findall(r"\w+", (row["title"] + " " + row["snippet"]).lower()))
        )
        rows.append(row)
    return sorted(rows, key=lambda r: -r["query_term_overlap"])


def verify_claims(claims, citations):
    by_id = {c["citation_id"]: c for c in citations}
    records = []
    for claim in claims:
        c = by_id.get(claim.get("citation_id"))
        text = claim.get("text", "")
        evidence = (
            (c.get("full_text_excerpt") or c.get("search_snippet") or "") if c else ""
        )
        expected = (
            hashlib.sha256((c["url"] + evidence).encode()).hexdigest() if c else None
        )
        supported = bool(
            c
            and text.strip()
            and text in evidence
            and c.get("content_hash") == expected
        )
        records.append(
            {
                "text": text,
                "citation_id": claim.get("citation_id"),
                "supported": supported,
                "reason": "exact extract with intact evidence hash"
                if supported
                else "missing citation, unsupported text or evidence hash mismatch",
            }
        )
    return {
        "claims": records,
        "supported": sum(r["supported"] for r in records),
        "unsupported": sum(not r["supported"] for r in records),
        "scope": "Literal support only, not semantic entailment, source truth or currentness",
    }


class Verification(BaseModel):
    claims: list[dict] = Field(max_length=20)
    citations: list[dict] = Field(max_length=10)


def router():
    routes = APIRouter(prefix="/api/answers", tags=["answer verification"])

    @routes.post("/verify")
    def verify(body: Verification):
        # User-supplied evidence is explicitly untrusted; cannot authorize any action.
        try:
            return verify_claims(body.claims, body.citations)
        except (KeyError, TypeError, AttributeError):
            return {
                "status": "invalid_evidence",
                "supported": 0,
                "execution_authorized": False,
            }

    return routes
