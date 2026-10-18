from test_api import client  # noqa: F401

from nexora import search as search_module


def test_health_reports_each_provider(client, monkeypatch):  # noqa: F811
    def fake_search(self, query, limit=5, options=None):
        return [
            search_module.SearchResult("t", "https://x", "s", "pub", self.name, "now")
        ]

    for provider in search_module.PROVIDERS.values():
        monkeypatch.setattr(type(provider), "search", fake_search)
    out = client.get("/api/search/health").json()
    for name in search_module.PROVIDERS:
        assert out[name] == "reachable"
    for name in search_module.NOT_IMPLEMENTED_NO_KEY:
        assert "not implemented" in out[name] or "key present" in out[name]


def test_search_normalizes_and_dedupes(client, monkeypatch):  # noqa: F811
    def fake_wikipedia(self, query, limit=5, options=None):
        return [
            search_module.SearchResult(
                "Dup",
                "https://en.wikipedia.org/wiki/Dup",
                "s1",
                "Wikipedia",
                "wikipedia",
                "now",
            ),
            search_module.SearchResult(
                "Dup",
                "https://en.wikipedia.org/wiki/Dup",
                "s1",
                "Wikipedia",
                "wikipedia",
                "now",
            ),
        ]

    monkeypatch.setattr(search_module.WikipediaProvider, "search", fake_wikipedia)
    out = client.post(
        "/api/search", json={"query": "python", "providers": ["wikipedia"], "limit": 5}
    ).json()
    assert len(out["results"]) == 1
    assert out["results"][0]["provider"] == "wikipedia"
    assert out["errors"] == {}


def test_search_one_provider_failure_does_not_sink_others(client, monkeypatch):  # noqa: F811
    def failing(self, query, limit=5, options=None):
        raise RuntimeError("simulated outage")

    def working(self, query, limit=5, options=None):
        return [
            search_module.SearchResult("ok", "https://ok", "s", "pub", self.name, "now")
        ]

    monkeypatch.setattr(search_module.WikipediaProvider, "search", failing)
    monkeypatch.setattr(search_module.ArxivProvider, "search", working)
    out = client.post(
        "/api/search",
        json={"query": "x", "providers": ["wikipedia", "arxiv"], "limit": 5},
    ).json()
    assert "simulated outage" in out["errors"]["wikipedia"]
    assert len(out["results"]) == 1
    assert out["results"][0]["provider"] == "arxiv"


def test_search_rejects_unknown_provider(client):  # noqa: F811
    assert (
        client.post(
            "/api/search", json={"query": "x", "providers": ["not-a-real-provider"]}
        ).status_code
        == 422
    )


def test_search_rejects_oversized_query(client):  # noqa: F811
    assert client.post("/api/search", json={"query": "a" * 401}).status_code == 422


def test_search_result_caches_identical_requests(client, monkeypatch):  # noqa: F811
    calls = []

    def counting(self, query, limit=5, options=None):
        calls.append(1)
        return [
            search_module.SearchResult("t", "https://x", "s", "pub", self.name, "now")
        ]

    monkeypatch.setattr(search_module.WikipediaProvider, "search", counting)
    search_module._cache.clear()
    client.post("/api/search", json={"query": "cache-me", "providers": ["wikipedia"]})
    client.post("/api/search", json={"query": "cache-me", "providers": ["wikipedia"]})
    assert len(calls) == 1
