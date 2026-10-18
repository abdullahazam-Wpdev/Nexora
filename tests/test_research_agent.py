from test_api import client  # noqa: F401

from nexora import research_agent


def test_no_sources_found_is_reported_not_hidden(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(
        research_agent,
        "run_search",
        lambda q, p, limit=5: {
            "query": q,
            "results": [],
            "errors": {"wikipedia": "boom"},
        },
    )
    out = client.post("/api/research/ask", json={"question": "anything"}).json()
    assert out["status"] == "no_sources_found"
    assert out["citations"] == []
    assert out["answer"] is None


def test_answer_built_only_from_retrieved_citations(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(
        research_agent,
        "run_search",
        lambda q, p, limit=5: {
            "query": q,
            "results": [
                {
                    "title": "Example Title",
                    "url": "https://example.com/a",
                    "snippet": "a short snippet",
                    "publisher": "Example",
                    "provider": "wikipedia",
                    "retrieved_at": "now",
                    "published_at": None,
                    "relevance": {},
                    "content_hash": "abc",
                }
            ],
            "errors": {},
        },
    )
    monkeypatch.setattr(
        research_agent,
        "read_url",
        lambda url: {"text": "The real article body text.", "url": url},
    )
    out = client.post(
        "/api/research/ask", json={"question": "q", "providers": ["wikipedia"]}
    ).json()
    assert out["status"] == "answered_with_evidence"
    assert len(out["citations"]) == 1
    citation = out["citations"][0]
    assert citation["url"] == "https://example.com/a"
    assert citation["read_status"] == "read"
    assert "real article body text" in citation["full_text_excerpt"]
    assert "[c1]" in out["answer"]
    assert "real article body text" in out["answer"]
    assert out["answer_kind"].startswith("extractive_summary")


def test_read_failure_is_recorded_not_swallowed(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(
        research_agent,
        "run_search",
        lambda q, p, limit=5: {
            "query": q,
            "results": [
                {
                    "title": "T",
                    "url": "https://example.com/a",
                    "snippet": "snippet text",
                    "publisher": "P",
                    "provider": "wikipedia",
                    "retrieved_at": "now",
                    "published_at": None,
                    "relevance": {},
                    "content_hash": "abc",
                }
            ],
            "errors": {},
        },
    )

    def failing_read(url):
        raise RuntimeError("Navigation failed: timeout")

    monkeypatch.setattr(research_agent, "read_url", failing_read)
    out = client.post("/api/research/ask", json={"question": "q"}).json()
    citation = out["citations"][0]
    assert citation["read_status"].startswith("failed:")
    assert "https://example.com/a" in out["read_errors"]
    # Falls back to the real search snippet, not a fabricated excerpt.
    assert "snippet text" in out["answer"]


def test_rejects_unknown_provider(client):  # noqa: F811
    out = client.post(
        "/api/research/ask", json={"question": "q", "providers": ["not-real"]}
    )
    assert out.status_code == 422
