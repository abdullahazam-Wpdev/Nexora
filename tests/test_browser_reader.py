from test_api import client  # noqa: F401

from nexora import browser_reader


def test_validate_url_rejects_private_and_non_http():
    for bad in [
        "http://127.0.0.1/",
        "http://localhost:8000/",
        "file:///etc/passwd",
        "ftp://example.com",
        "http://169.254.169.254/",  # link-local metadata endpoint
    ]:
        try:
            browser_reader._validate_url(bad)
            assert False, f"should have rejected {bad}"
        except ValueError:
            pass


def test_read_endpoint_mocked(client, monkeypatch):  # noqa: F811
    def fake_read(url, screenshot=False):
        return {
            "url": url,
            "title": "Example",
            "text": "hello world",
            "headings": ["Example"],
            "links": [{"href": "https://example.com/other", "text": "other"}],
            "screenshot_path": None,
            "truncated": False,
        }

    monkeypatch.setattr(browser_reader, "read_url", fake_read)
    out = client.post("/api/browser/read", json={"url": "https://example.com"})
    assert out.status_code == 200
    assert out.json()["title"] == "Example"
    assert out.json()["text"] == "hello world"


def test_read_endpoint_rejects_invalid_url(client, monkeypatch):  # noqa: F811
    def fake_read(url, screenshot=False):
        raise ValueError("Only http/https URLs are allowed")

    monkeypatch.setattr(browser_reader, "read_url", fake_read)
    out = client.post("/api/browser/read", json={"url": "file:///etc/passwd"})
    assert out.status_code == 422


def test_read_endpoint_reports_navigation_failure(client, monkeypatch):  # noqa: F811
    def fake_read(url, screenshot=False):
        raise RuntimeError("Navigation failed: timeout")

    monkeypatch.setattr(browser_reader, "read_url", fake_read)
    out = client.post("/api/browser/read", json={"url": "https://example.com"})
    assert out.status_code == 502


def test_find_endpoint_mocked(client, monkeypatch):  # noqa: F811
    def fake_find(url, phrase):
        return {"url": url, "phrase": phrase, "matches": ["...context..."]}

    monkeypatch.setattr(browser_reader, "find_in_page", fake_find)
    out = client.post(
        "/api/browser/find", json={"url": "https://example.com", "phrase": "hello"}
    )
    assert out.status_code == 200
    assert out.json()["matches"] == ["...context..."]


def test_read_endpoint_rejects_oversized_url(client):  # noqa: F811
    assert (
        client.post(
            "/api/browser/read", json={"url": "https://x/" + "a" * 2000}
        ).status_code
        == 422
    )
