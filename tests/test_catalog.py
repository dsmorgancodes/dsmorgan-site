import re
from datetime import date

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.extension import db
from app.models import PortfolioEntry


def token(response):
    return re.search(
        r'name="csrf_token"[^>]*value="([^"]+)"', response.get_data(as_text=True)
    ).group(1)


def login(client):
    csrf = token(client.get("/admin/login"))
    response = client.post(
        "/admin/login",
        data={
            "csrf_token": csrf,
            "username": "admin",
            "password": "test-only-password",
        },
    )
    assert response.status_code == 302


def entry_data(csrf, **overrides):
    data = {
        "csrf_token": csrf,
        "title": "A paper",
        "entry_type": "paper",
        "written_date": "2025-04-12",
        "link": "https://example.com/paper",
        "version_control_url": "",
    }
    data.update(overrides)
    return data


def test_catalog_lifecycle(client, app):
    login(client)
    csrf = token(client.get("/admin/entries/new"))
    assert client.post("/admin/entries/new", data=entry_data(csrf)).status_code == 302
    assert b"A paper" not in client.get("/work").data
    assert b"Draft" in client.get("/admin").data
    with app.app_context():
        entry = db.session.execute(db.select(PortfolioEntry)).scalar_one()
        entry_id = entry.id
        assert entry.written_date == date(2025, 4, 12)
        assert entry.version_control_url is None

    path = f"/admin/entries/{entry_id}/edit"
    csrf = token(client.get(path))
    assert (
        client.post(
            path,
            data=entry_data(
                csrf,
                published="y",
                version_control_url="https://github.com/example/paper",
                summary="  A short abstract.  ",
            ),
        ).status_code
        == 302
    )
    work = client.get("/work").data
    assert b"A paper" in work
    assert b"Version Control" in work
    assert b'<p class="card-summary">A short abstract.</p>' in work

    csrf = token(client.get(path))
    assert (
        client.post(
            path, data=entry_data(csrf, title="Updated paper", written_date="")
        ).status_code
        == 302
    )
    assert b"Updated paper" in client.get("/admin").data
    assert b"Updated paper" not in client.get("/work").data

    path = f"/admin/entries/{entry_id}/delete"
    page = client.get(path)
    assert b"Delete entry?" in page.data
    with app.app_context():
        assert db.session.get(PortfolioEntry, entry_id) is not None
    assert client.post(path, data={"csrf_token": token(page)}).status_code == 302
    assert b"No entries yet" in client.get("/admin").data


@pytest.mark.parametrize(
    "path",
    [
        "/admin",
        "/admin/entries/new",
        "/admin/entries/1/edit",
        "/admin/entries/1/delete",
    ],
)
def test_requires_login(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": " "},
        {"title": "x" * 201},
        {"entry_type": "other"},
        {"written_date": "not-a-date"},
        {"link": "javascript:alert(1)"},
        {"link": "ftp://example.com/paper"},
        {"version_control_url": "javascript:alert(1)"},
    ],
)
def test_invalid_entries_are_not_saved(client, app, overrides):
    login(client)
    csrf = token(client.get("/admin/entries/new"))
    response = client.post("/admin/entries/new", data=entry_data(csrf, **overrides))
    assert response.status_code == 200
    assert b'role="alert"' in response.data
    with app.app_context():
        assert db.session.execute(db.select(PortfolioEntry)).first() is None


def test_csrf_and_logout(client, app):
    login(client)
    assert client.post("/admin/entries/new", data=entry_data("")).status_code == 400
    assert client.post("/admin/logout").status_code == 400
    assert client.get("/admin/logout").status_code == 405
    csrf = token(client.get("/admin"))
    assert client.post("/admin/logout", data={"csrf_token": csrf}).status_code == 302
    assert client.get("/admin").status_code == 302


def test_missing_entries(client):
    login(client)
    assert client.get("/admin/entries/999/edit").status_code == 404
    assert client.get("/admin/entries/999/delete").status_code == 404


def test_failed_write_is_reported(client, app, monkeypatch):
    login(client)
    csrf = token(client.get("/admin/entries/new"))

    def fail_commit():
        raise SQLAlchemyError("simulated database failure")

    monkeypatch.setattr(db.session, "commit", fail_commit)
    response = client.post("/admin/entries/new", data=entry_data(csrf))
    assert response.status_code == 503
    assert b"could not save your change" in response.data
    with app.app_context():
        assert db.session.execute(db.select(PortfolioEntry)).first() is None


BOOK = ["/", "/studies", "/work", "/cv", "/contact"]


def test_index_lists_contents_and_assets(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    for path in BOOK[1:]:
        assert f'href="{path}"' in html
    assert 'href="#main-content"' in html
    assert 'class="terminal-nav" aria-label="Main navigation"' in html
    assert 'class="ribbon"' not in html
    assert 'rel="canonical" href="https://dsmorgan.com/"' in html
    assert 'rel="icon" href="/static/favicon.svg?v=' in html
    assert "/admin" not in html
    for sheet in ("tokens", "base", "components", "pages", "terminal"):
        assert f"/static/css/{sheet}.css" in html
        assert client.get(f"/static/css/{sheet}.css").status_code == 200
    for asset in ("paper-grain.svg", "favicon.svg", "fonts/eb-garamond-LICENSE.txt"):
        assert client.get(f"/static/{asset}").status_code == 200
    assert client.get("/favicon.ico").status_code == 301
    css = client.get("/static/css/base.css").get_data(as_text=True)
    assert "cursor: url(" not in css
    assert "@view-transition" in css
    for font_file in ("eb-garamond-latin", "eb-garamond-italic-latin"):
        font = client.get(f"/static/fonts/{font_file}.woff2")
        assert font.status_code == 200
        assert font.data[:4] == b"wOF2"


@pytest.mark.parametrize("position", range(len(BOOK)))
def test_pages_have_current_navigation(client, position):
    html = client.get(BOOK[position]).get_data(as_text=True)
    assert f'<a href="{BOOK[position]}" aria-current="page">' in html
    assert html.count('aria-current="page"') == 1
    assert '<meta property="og:title"' in html
    assert 'class="folio"' not in html
    assert 'class="page-turn"' not in html


def test_page_content(client):
    assert b"Topology" in client.get("/studies").data
    assert b"Papers and projects are coming soon." in client.get("/work").data
    assert b'href="mailto:drew@dsmorgan.com"' in client.get("/contact").data
    cv = client.get("/cv").get_data(as_text=True)
    assert "Northwest Missouri State University" in cv
    assert 'id="request"' in cv
    assert "challenges.cloudflare.com" not in cv


def test_missing_page_uses_terminal_404(client):
    response = client.get("/no-such-volume")
    assert response.status_code == 404
    assert b"404: Page not found" in response.data
    assert b'name="robots" content="noindex"' in response.data


def test_public_catalog_order_and_escaping(client, app):
    with app.app_context():
        db.session.add_all(
            [
                PortfolioEntry(
                    title="Earlier work",
                    entry_type="paper",
                    link="https://example.com/a",
                    written_date=date(2020, 1, 1),
                    published=True,
                ),
                PortfolioEntry(
                    title="<script>Latest work</script>",
                    entry_type="project",
                    link="https://example.com/b",
                    written_date=date(2025, 1, 1),
                    published=True,
                ),
                PortfolioEntry(
                    title="Undated work",
                    entry_type="paper",
                    link="https://example.com/c",
                    published=True,
                ),
                PortfolioEntry(
                    title="Hidden draft",
                    entry_type="paper",
                    link="https://example.com/d",
                    published=False,
                ),
            ]
        )
        db.session.commit()
    html = client.get("/work").get_data(as_text=True)
    assert (
        html.index("Latest work")
        < html.index("Earlier work")
        < html.index("Undated work")
    )
    assert "&lt;script&gt;Latest work&lt;/script&gt;" in html
    assert "<script>Latest work</script>" not in html
    assert "Hidden draft" not in html
    assert 'datetime="2025-01-01"' in html
