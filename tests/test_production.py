import re

import pytest

from app import create_app
from tests.test_catalog import login, token


def test_security_headers_are_set(client):
    response = client.get("/")
    headers = response.headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "Referrer-Policy" in headers
    assert "Strict-Transport-Security" not in headers


def test_hsts_only_over_https(client):
    response = client.get("/", headers={"X-Forwarded-Proto": "https"})
    assert "max-age=31536000" in response.headers["Strict-Transport-Security"]


def test_admin_pages_are_not_cached(client):
    response = client.get("/admin/login")
    assert response.headers["Cache-Control"] == "no-store"


def test_static_assets_are_versioned(client):
    html = client.get("/").get_data(as_text=True)
    href = re.search(r'href="(/static/css/tokens\.css\?v=[0-9a-f]{10})"', html)
    assert href
    versioned = client.get(href.group(1))
    assert "max-age=31536000" in versioned.headers["Cache-Control"]
    plain = client.get("/static/css/tokens.css")
    assert "max-age=3600" in plain.headers["Cache-Control"]


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_robots_and_sitemap(client):
    robots = client.get("/robots.txt").get_data(as_text=True)
    assert "Disallow: /admin" in robots
    assert "Sitemap: https://dsmorgan.com/sitemap.xml" in robots
    sitemap = client.get("/sitemap.xml")
    assert sitemap.mimetype == "application/xml"
    body = sitemap.get_data(as_text=True)
    assert "<loc>https://dsmorgan.com/</loc>" in body
    assert "/admin" not in body


def fail_login(client):
    csrf = token(client.get("/admin/login"))
    return client.post(
        "/admin/login",
        data={"csrf_token": csrf, "username": "admin", "password": "wrong"},
    )


def test_login_failures_are_rate_limited(client):
    for _ in range(5):
        assert fail_login(client).status_code == 200
    assert fail_login(client).status_code == 429


def test_successful_login_clears_failures(app, client):
    for _ in range(4):
        fail_login(client)
    login(client)
    fresh = app.test_client()
    for _ in range(5):
        assert fail_login(fresh).status_code == 200


def test_factory_requires_secret_key(monkeypatch):
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="FLASK_SECRET_KEY"):
        create_app()


def test_cookies_are_secure_by_default(monkeypatch):
    monkeypatch.setenv("FLASK_SECRET_KEY", "x")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.delenv("FLASK_DEBUG", raising=False)
    app = create_app()
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["REMEMBER_COOKIE_SECURE"] is True
    assert app.config["PREFERRED_URL_SCHEME"] == "https"
