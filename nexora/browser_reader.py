"""Bounded, isolated browser reading for the research agent.

Live-verified this session: a fresh headless Chromium instance
(`/var/cache/ms-playwright`, already installed) can navigate to a real
public page and extract real visible text -- this is not a stub.

Isolation and safety, by construction:
- Every call launches a brand-new headless browser context with no
  profile, no saved cookies, no saved passwords, and no user data
  directory -- there is nothing to leak because nothing persists between
  calls or is shared with the owner's real browser.
- Only `http`/`https` URLs are accepted; anything else (file://, javascript:,
  data:, etc.) is rejected before launch.
- Private/loopback/link-local targets are rejected (a basic SSRF guard) so
  this tool cannot be used to probe the local network or other services on
  this machine. Authenticated sites are out of scope entirely: there is no
  login flow, no stored session, and no way to pass credentials in.
- Only one browser session runs at a time (a lock), bounding memory use on
  this 7.5 GiB machine.
- Returned page text is DATA, not instructions. A page's content may
  contain text that looks like a command aimed at an AI agent; it must
  never be treated as one. Callers (the research agent) must wrap this
  text as untrusted evidence, the same discipline this project already
  applies to REA tool output.
"""

import ipaddress
import socket
import threading
import time
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nexora.config import STORE

MAX_TEXT_CHARS = 20000
MAX_LINKS = 40
NAV_TIMEOUT_MS = 15000
_lock = threading.Lock()


def _validate_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http/https URLs are allowed")
    if parsed.username or parsed.password:
        raise ValueError("Credentials in URLs are not allowed")
    if not parsed.hostname:
        raise ValueError("URL has no host")
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except OSError as exc:
        raise ValueError(f"Could not resolve host: {exc}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            raise ValueError("Refusing to navigate to a private/internal address")
    return url


def read_url(url, screenshot=False):
    """Open url, return {title, text, headings, links, screenshot_path}.
    Raises ValueError for bad input, RuntimeError for navigation failure.
    Blocks until any other browser read finishes (one session at a time)."""
    from playwright.sync_api import sync_playwright

    _validate_url(url)
    if not _lock.acquire(timeout=30):
        raise RuntimeError("Browser is busy with another request; try again shortly")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                # Validate every document navigation, including redirects/frames.
                # Block active scripts and subresources in this read-only profile.
                navigation_count = [0]

                def guard(route):
                    if route.request.resource_type != "document":
                        route.abort()
                        return
                    navigation_count[0] += 1
                    try:
                        if navigation_count[0] > 12:
                            raise ValueError("Navigation budget exceeded")
                        _validate_url(route.request.url)
                        route.continue_()
                    except ValueError:
                        route.abort()

                page.route("**/*", guard)

                try:
                    page.goto(
                        url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS
                    )
                except Exception as exc:
                    raise RuntimeError(f"Navigation failed: {exc}") from exc
                title = page.title()
                # Prefer the actual article/content container over the full
                # page body, which is mostly navigation chrome on most
                # sites (confirmed on Wikipedia this session: raw <body>
                # text starts with "Jump to content / Main menu / Search
                # / Donate..." before any article content). Fall back to
                # <body> only if none of these containers exist.
                full_text = None
                for selector in (
                    "#mw-content-text",  # MediaWiki (Wikipedia and others)
                    "article",
                    "main",
                    "#content",
                ):
                    locator = page.locator(selector).first
                    if locator.count() > 0:
                        candidate = locator.inner_text().strip()
                        if len(candidate) > 200:
                            full_text = candidate
                            break
                if full_text is None:
                    full_text = page.inner_text("body")
                text = full_text[:MAX_TEXT_CHARS]
                headings = [
                    h.inner_text().strip()
                    for h in page.locator("h1, h2, h3").all()[:30]
                    if h.inner_text().strip()
                ]
                links = []
                for a in page.locator("a[href]").all()[: MAX_LINKS * 3]:
                    href = a.get_attribute("href")
                    label = (a.inner_text() or "").strip()
                    if href and href.startswith(("http://", "https://")):
                        links.append({"href": href, "text": label[:120]})
                    if len(links) >= MAX_LINKS:
                        break
                screenshot_path = None
                if screenshot:
                    out_dir = STORE / "browser-evidence"
                    out_dir.mkdir(exist_ok=True)
                    screenshot_path = str(out_dir / f"{int(time.time() * 1000)}.png")
                    page.screenshot(path=screenshot_path)
                return {
                    "url": page.url,
                    "title": title,
                    "text": text,
                    "headings": headings,
                    "links": links,
                    "screenshot_path": screenshot_path,
                    "truncated": len(full_text) > MAX_TEXT_CHARS,
                }
            finally:
                browser.close()
    finally:
        _lock.release()


def find_in_page(url, phrase):
    """Bounded in-page search: return surrounding context for each match."""
    data = read_url(url)
    text = data["text"]
    lower_text, lower_phrase = text.lower(), phrase.lower()
    matches = []
    start = 0
    while len(matches) < 10:
        idx = lower_text.find(lower_phrase, start)
        if idx == -1:
            break
        matches.append(text[max(0, idx - 80) : idx + len(phrase) + 80])
        start = idx + len(phrase)
    return {"url": url, "phrase": phrase, "matches": matches}


class ReadRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2000)
    screenshot: bool = False


class FindRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2000)
    phrase: str = Field(min_length=1, max_length=200)


def router(audit):
    routes = APIRouter(prefix="/api/browser", tags=["browser automation"])

    @routes.post("/read")
    def read(body: ReadRequest):
        try:
            result = read_url(body.url, body.screenshot)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(502, str(exc)) from exc
        audit(
            "browser.read",
            f"{body.url} -> {len(result['text'])} chars, {len(result['links'])} links",
        )
        return result

    @routes.post("/find")
    def find(body: FindRequest):
        try:
            result = find_in_page(body.url, body.phrase)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(502, str(exc)) from exc
        audit(
            "browser.find",
            f"{body.url} phrase={body.phrase!r} matches={len(result['matches'])}",
        )
        return result

    return routes
