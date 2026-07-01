"""pytest suite for the URL shortener: happy-path roundtrip, analytics,
custom aliases, and the malicious-input / SSRF rejection paths.

DNS resolution for "public" test URLs is monkeypatched so these tests run
deterministically without live network access; SSRF-rejection tests use
literal IP addresses, which validators.py checks without any DNS lookup.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import validators
from app import app, store

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean_store():
    store._records.clear()
    yield
    store._records.clear()


@pytest.fixture(autouse=True)
def _mock_public_dns(monkeypatch):
    """Any hostname resolves to a public IP unless the test overrides it,
    so "https://example.com/..."-style URLs don't depend on real DNS."""

    def fake_getaddrinfo(host, port, *args, **kwargs):
        ip = "127.0.0.1" if host == "localhost" else "93.184.216.34"
        return [(2, 1, 6, "", (ip, 0))]

    monkeypatch.setattr(validators.socket, "getaddrinfo", fake_getaddrinfo)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_shorten_and_redirect_roundtrip():
    resp = client.post("/api/shorten", json={"url": "https://example.com/some/path"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["long_url"] == "https://example.com/some/path"
    code = body["code"]
    assert len(code) == 7

    redirect = client.get(f"/{code}", follow_redirects=False)
    assert redirect.status_code == 307
    assert redirect.headers["location"] == "https://example.com/some/path"


def test_stats_endpoint_tracks_clicks():
    code = client.post("/api/shorten", json={"url": "https://example.com/a"}).json()["code"]

    client.get(f"/{code}", follow_redirects=False)
    client.get(f"/{code}", follow_redirects=False)

    stats = client.get(f"/api/stats/{code}").json()
    assert stats["clicks"] == 2
    assert stats["last_accessed_at"] is not None


def test_unknown_code_returns_404():
    resp = client.get("/api/stats/doesnotexist")
    assert resp.status_code == 404


def test_custom_alias_happy_path():
    resp = client.post(
        "/api/shorten", json={"url": "https://example.com/x", "custom_alias": "my-link"}
    )
    assert resp.status_code == 201
    assert resp.json()["code"] == "my-link"


def test_custom_alias_collision_returns_409():
    client.post("/api/shorten", json={"url": "https://example.com/x", "custom_alias": "taken"})
    resp = client.post(
        "/api/shorten", json={"url": "https://example.com/y", "custom_alias": "taken"}
    )
    assert resp.status_code == 409


def test_custom_alias_invalid_characters_rejected():
    resp = client.post(
        "/api/shorten", json={"url": "https://example.com/x", "custom_alias": "not valid!"}
    )
    assert resp.status_code == 422


def test_custom_alias_reserved_word_rejected():
    resp = client.post(
        "/api/shorten", json={"url": "https://example.com/x", "custom_alias": "health"}
    )
    assert resp.status_code == 422


@pytest.mark.parametrize(
    "malicious_url",
    [
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
        "ftp://example.com/file",
    ],
)
def test_disallowed_schemes_rejected(malicious_url):
    resp = client.post("/api/shorten", json={"url": malicious_url})
    assert resp.status_code == 422
    assert "scheme" in resp.json()["detail"]


@pytest.mark.parametrize(
    "ssrf_url",
    [
        "http://127.0.0.1/admin",
        "http://localhost/admin",
        "http://10.0.0.5/internal",
        "http://169.254.169.254/latest/meta-data/",
        "http://0.0.0.0/",
    ],
)
def test_ssrf_targets_rejected(ssrf_url):
    resp = client.post("/api/shorten", json={"url": ssrf_url})
    assert resp.status_code == 422
    assert "SSRF" in resp.json()["detail"] or "private" in resp.json()["detail"].lower()


def test_oversized_url_rejected():
    huge_url = "https://example.com/" + "a" * 3000
    resp = client.post("/api/shorten", json={"url": huge_url})
    assert resp.status_code == 422


def test_delete_removes_code():
    code = client.post("/api/shorten", json={"url": "https://example.com/z"}).json()["code"]
    resp = client.delete(f"/api/{code}")
    assert resp.status_code == 204
    assert client.get(f"/api/stats/{code}").status_code == 404


def test_delete_unknown_code_returns_404():
    resp = client.delete("/api/doesnotexist")
    assert resp.status_code == 404
