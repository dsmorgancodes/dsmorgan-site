import pytest


@pytest.mark.parametrize(
    "path", ["/", "/studies", "/work", "/cv", "/contact", "/admin/login", "/missing"]
)
def test_theme_control_on_every_page(client, path):
    html = client.get(path).get_data(as_text=True)
    assert 'aria-label="Switch to Everforest Dark"' in html
    assert 'class="theme-toggle"' in html
    assert 'aria-pressed="false"' in html
    assert "/static/js/theme.js?v=" in html
    assert html.index("/static/js/theme.js") < html.index("/static/css/tokens.css")
    assert "/static/css/terminal.css?v=" in html
    assert ">D.S. Morgan</a>" in html
    assert ":~$" not in html
    assert "$ cat " not in html
    assert ">~/ " not in html


def test_research_homepage(client):
    html = client.get("/").get_data(as_text=True)
    assert "My work brings together mathematics" in html
    assert "Explore selected work" in html
    assert 'class="workbench-grid"' in html
    assert 'class="toc-numeral"' not in html
    assert 'class="footer-links"' in html


def test_homepage_education_and_workbench(client):
    html = client.get("/").get_data(as_text=True)
    assert 'aria-labelledby="education-heading"' in html
    assert "Master of Science" in html
    assert "Northwest Missouri State University" in html
    assert "Bachelor of Science" in html
    assert "Olivet Nazarene University" in html
    assert 'href="/cv">View experience &amp; request full CV' in html
    for heading in ("studies-heading", "work-heading", "collaboration-heading"):
        assert f'aria-labelledby="{heading}"' in html
    assert 'href="/studies">Explore studies' in html
    assert 'href="/work">Browse work' in html
    assert 'href="/contact">Get in touch' in html


def test_theme_assets_available(client):
    assert client.get("/static/js/theme.js").status_code == 200
    css = client.get("/static/css/terminal.css").get_data(as_text=True)
    for variant in ("light", "dark"):
        assert f'[data-theme="{variant}"]' in css
