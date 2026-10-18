"""Unified internet search interface.

Live-verified reachable from this environment with NO API key (2026-10-18):
Wikipedia/MediaWiki, arXiv, Crossref, GitHub code/repo search. Brave,
Tavily, Exa, Serper and Bing-compatible APIs are NOT implemented because no
credential for any of them is configured anywhere in this project
(checked via environment variables only; never hardcoded) -- adding an
adapter for a paid/keyed service with no key to test it against would be
unverifiable code, so it is deferred rather than guessed at. See
docs/WEB_SEARCH_INTEGRATION.md for exactly what was checked.

Every result is normalized to: title, url, snippet, publisher,
published_at (if available), retrieved_at, provider, relevance metadata.
Nothing here fabricates a URL or snippet; a provider that fails returns an
empty list plus a recorded error, never invented results.
"""

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pydantic import Field as PField

from nexora.config import STORE

TIMEOUT = 10
MAX_RETRIES = 2
CACHE_SECONDS = 300
_cache = {}
# Wikipedia's API etiquette (https://www.mediawiki.org/wiki/API:Etiquette,
# already cited in docs/provider-capabilities.md) requires a descriptive
# User-Agent identifying the application and a contact method; the default
# httpx/curl user agent is throttled/blocked with 403. GitHub's REST API
# likewise requires a User-Agent on every request.
USER_AGENT = (
    "NEXORA-AI-OS/0.2 (local research assistant; "
    "https://github.com/abdullahazam-Wpdev/Nexora; contact via GitHub issues)"
)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    publisher: str
    provider: str
    retrieved_at: str
    published_at: str | None = None
    relevance: dict = field(default_factory=dict)
    content_hash: str = ""

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.sha256(
                (self.url + self.snippet).encode()
            ).hexdigest()


def _get(url, params, headers=None):
    last_exc = None
    merged_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    for attempt in range(MAX_RETRIES + 1):
        try:
            with httpx.Client(trust_env=False, timeout=TIMEOUT) as client:
                response = client.get(url, params=params, headers=merged_headers)
            if response.status_code == 429:
                raise RuntimeError("rate limited")
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, RuntimeError, ValueError) as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(
        f"{url} unreachable after {MAX_RETRIES + 1} attempts: {last_exc}"
    )


class SearchProvider:
    name = "base"
    requires_key = False

    def available(self):
        return True

    def search(self, query, limit=5, options=None):
        raise NotImplementedError


class WikipediaProvider(SearchProvider):
    name = "wikipedia"

    def search(self, query, limit=5, options=None):
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        data = _get(
            "https://en.wikipedia.org/w/api.php",
            {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": min(limit, 10),
            },
        )
        results = []
        for i, item in enumerate(data.get("query", {}).get("search", [])):
            snippet = (
                item.get("snippet", "")
                .replace('<span class="searchmatch">', "")
                .replace("</span>", "")
            )
            results.append(
                SearchResult(
                    title=item["title"],
                    url="https://en.wikipedia.org/wiki/"
                    + item["title"].replace(" ", "_"),
                    snippet=snippet,
                    publisher="Wikipedia",
                    provider=self.name,
                    retrieved_at=now,
                    published_at=item.get("timestamp"),
                    relevance={"rank": i, "wordcount": item.get("wordcount")},
                )
            )
        return results


class ArxivProvider(SearchProvider):
    name = "arxiv"

    def search(self, query, limit=5, options=None):
        import xml.etree.ElementTree as ET

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for attempt in range(MAX_RETRIES + 1):
            try:
                with httpx.Client(trust_env=False, timeout=TIMEOUT) as client:
                    response = client.get(
                        "https://export.arxiv.org/api/query",
                        params={
                            "search_query": f"all:{query}",
                            "max_results": min(limit, 10),
                        },
                        headers={"User-Agent": USER_AGENT},
                    )
                response.raise_for_status()
                break
            except httpx.HTTPError as exc:
                if attempt == MAX_RETRIES:
                    raise RuntimeError(f"arxiv unreachable: {exc}") from exc
                time.sleep(0.5 * (attempt + 1))
        ns = {"a": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(response.text)
        results = []
        for i, entry in enumerate(root.findall("a:entry", ns)):
            title = entry.findtext("a:title", default="", namespaces=ns).strip()
            url = entry.findtext("a:id", default="", namespaces=ns).strip()
            summary = entry.findtext("a:summary", default="", namespaces=ns).strip()
            published = entry.findtext("a:published", default=None, namespaces=ns)
            authors = [
                a.findtext("a:name", default="", namespaces=ns)
                for a in entry.findall("a:author", ns)
            ]
            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=summary[:500],
                    publisher=", ".join(authors) or "arXiv",
                    provider=self.name,
                    retrieved_at=now,
                    published_at=published,
                    relevance={"rank": i},
                )
            )
        return results


class CrossrefProvider(SearchProvider):
    name = "crossref"

    def search(self, query, limit=5, options=None):
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        data = _get(
            "https://api.crossref.org/works",
            {"query": query, "rows": min(limit, 10)},
        )
        results = []
        for i, item in enumerate(data.get("message", {}).get("items", [])):
            title = " ".join(item.get("title", [])) or "(untitled)"
            results.append(
                SearchResult(
                    title=title,
                    url=item.get("URL", ""),
                    snippet=" ".join(item.get("container-title", [])),
                    publisher=" / ".join(item.get("publisher", "").split(", "))
                    or "Crossref",
                    provider=self.name,
                    retrieved_at=now,
                    published_at=str(
                        item.get("created", {}).get("date-parts", [[None]])[0]
                    ),
                    relevance={"rank": i, "score": item.get("score")},
                )
            )
        return results


class GitHubProvider(SearchProvider):
    name = "github"

    def search(self, query, limit=5, options=None):
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        data = _get(
            "https://api.github.com/search/repositories",
            {"q": query, "per_page": min(limit, 10)},
            headers={"Accept": "application/vnd.github+json"},
        )
        results = []
        for i, item in enumerate(data.get("items", [])):
            results.append(
                SearchResult(
                    title=item.get("full_name", ""),
                    url=item.get("html_url", ""),
                    snippet=item.get("description") or "",
                    publisher="GitHub",
                    provider=self.name,
                    retrieved_at=now,
                    published_at=item.get("pushed_at"),
                    relevance={"rank": i, "stars": item.get("stargazers_count")},
                )
            )
        return results


PROVIDERS = {
    "wikipedia": WikipediaProvider(),
    "arxiv": ArxivProvider(),
    "crossref": CrossrefProvider(),
    "github": GitHubProvider(),
}

# Documented, keyed providers requested by Phase 6 that are not implemented
# because no credential exists for them in this environment. Listed, not
# silently omitted, so the registry is honest about what was checked.
NOT_IMPLEMENTED_NO_KEY = {
    "brave": "BRAVE_API_KEY",
    "tavily": "TAVILY_API_KEY",
    "exa": "EXA_API_KEY",
    "serper": "SERPER_API_KEY",
    "google-programmable-search": "GOOGLE_CSE_KEY",
    "bing": "BING_SEARCH_KEY",
}


def search(query, providers=None, limit=5):
    """Query one or more providers, dedupe by URL, return normalized results
    plus per-provider errors. Never raises for a provider failure -- that
    provider's slot in `errors` records it instead."""
    names = providers or list(PROVIDERS)
    cache_key = (query, tuple(sorted(names)), limit)
    now = time.monotonic()
    cached = _cache.get(cache_key)
    if cached and now - cached[0] < CACHE_SECONDS:
        return cached[1]
    all_results = []
    errors = {}
    for name in names:
        provider = PROVIDERS.get(name)
        if provider is None:
            errors[name] = (
                f"unknown or unconfigured provider; needs {NOT_IMPLEMENTED_NO_KEY.get(name, 'an adapter')}"
                if name in NOT_IMPLEMENTED_NO_KEY
                else "unknown provider"
            )
            continue
        try:
            all_results.extend(provider.search(query, limit))
        except Exception as exc:  # noqa: BLE001 -- one provider's failure must not sink the others
            errors[name] = str(exc)
    seen = set()
    deduped = []
    for r in all_results:
        if r.url in seen:
            continue
        seen.add(r.url)
        deduped.append(r)
    result = {"query": query, "results": [asdict(r) for r in deduped], "errors": errors}
    _cache[cache_key] = (now, result)
    return result


def health():
    status = {}
    for name, provider in PROVIDERS.items():
        try:
            provider.search("test", limit=1)
            status[name] = "reachable"
        except Exception as exc:  # noqa: BLE001
            status[name] = f"unreachable: {exc}"
    for name, key_env in NOT_IMPLEMENTED_NO_KEY.items():
        import os

        status[name] = (
            "not implemented (no adapter)"
            if not os.environ.get(key_env)
            else f"key present ({key_env}) but no adapter implemented yet"
        )
    return status


class SearchRequest(BaseModel):
    query: str = PField(min_length=1, max_length=400)
    providers: list[str] | None = None
    limit: int = PField(default=5, ge=1, le=10)


def router(audit):
    routes = APIRouter(prefix="/api/search", tags=["web search"])

    @routes.get("/health")
    def search_health():
        return health()

    @routes.post("")
    def do_search(body: SearchRequest):
        if body.providers:
            unknown = set(body.providers) - set(PROVIDERS)
            if unknown:
                raise HTTPException(422, f"Unknown provider(s): {sorted(unknown)}")
        result = search(body.query, body.providers, body.limit)
        audit(
            "search.query",
            json.dumps(
                {
                    "query": body.query,
                    "providers": body.providers or list(PROVIDERS),
                    "result_count": len(result["results"]),
                    "errors": result["errors"],
                }
            ),
        )
        (STORE / "search-evidence").mkdir(exist_ok=True)
        stamp = hashlib.sha256((body.query + str(time.time())).encode()).hexdigest()[
            :16
        ]
        (STORE / "search-evidence" / f"{stamp}.json").write_text(
            json.dumps(result, indent=2)
        )
        return result

    return routes
