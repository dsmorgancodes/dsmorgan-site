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
    toggle = html.split('<button class="theme-toggle"', 1)[1].split("</button>", 1)[0]
    assert 'shape-rendering="crispEdges"' in toggle
    assert 'stroke-linejoin="miter"' in toggle


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


@pytest.mark.parametrize("path", ["/studies", "/cv"])
def test_inner_page_accents(client, path):
    html = client.get(path).get_data(as_text=True)
    assert 'class="accent-page" aria-labelledby="page-heading"' in html
    assert "accent-page" not in client.get("/").get_data(as_text=True)


def test_study_symbols(client):
    from xml.etree import ElementTree

    html = client.get("/studies").get_data(as_text=True)
    glossary = html.split('<dl class="glossary">', 1)[1].split("</dl>", 1)[0]
    headings = ElementTree.fromstring(f"<dl>{glossary}</dl>").findall("./div/dt")
    assert len(headings) == 8
    assert headings[-1].find("span").text == "Abstract Algebra"
    for heading in headings:
        symbol = heading.find("svg")
        assert symbol is not None
        assert symbol.attrib["aria-hidden"] == "true"
        assert symbol.attrib["stroke"] == "currentColor"
        assert symbol.attrib["shape-rendering"] == "crispEdges"
        assert symbol.attrib["stroke-linejoin"] == "miter"
        assert len(symbol) > 0
        assert heading.find("span").text


def test_resume_section_symbols(client):
    from xml.etree import ElementTree

    html = client.get("/cv").get_data(as_text=True)
    headings = html.split('<h2 class="ledger-heading">')[1:]
    assert len(headings) == 3
    for markup, title in zip(headings, ("Education", "Positions", "Skills")):
        heading = ElementTree.fromstring("<h2>" + markup.split("</h2>", 1)[0] + "</h2>")
        symbol = heading.find("svg")
        assert symbol is not None
        assert symbol.attrib["aria-hidden"] == "true"
        assert symbol.attrib["stroke"] == "currentColor"
        assert symbol.attrib["shape-rendering"] == "crispEdges"
        assert symbol.attrib["stroke-linejoin"] == "miter"
        assert len(symbol) > 0
        assert heading.find("span").text == title
    assert html.count('class="resume-symbol"') == 3


def test_resume_education_gpa_badges(client):
    from xml.etree import ElementTree

    html = client.get("/cv").get_data(as_text=True)
    rows = html.split('<div class="ledger-entry education-row">')[1:]
    assert len(rows) == 2
    for markup, degree, gpa, years in zip(
        rows,
        ("M.S. in Mathematics", "B.S. in Mathematics"),
        ("4.00", "3.74"),
        ("2024–2026", "2017–2021"),
    ):
        content = markup.split("</span>", 1)[0].replace("&ndash;", "–")
        row = ElementTree.fromstring("<div>" + content + "</span></div>")
        assert row.find("div/h3").text == degree
        assert row.find('div/p[@class="education-years"]').text == years
        badge = row.find("span")
        assert badge.attrib["class"] == "gpa-badge"
        assert "".join(badge.itertext()) == f"GPA {gpa}"
    assert "gpa-badge" not in client.get("/").get_data(as_text=True)


@pytest.mark.parametrize(
    "path, title, intro",
    [
        ("/studies", "Areas of Study", "My graduate disciplines"),
        ("/cv", "Resume", "My work connects mathematics"),
        ("/work", "Selected Work", "Papers, coursework, and projects"),
        ("/contact", "Correspondence", "For research, collaboration"),
    ],
)
def test_inner_page_intro_panel(client, path, title, intro):
    html = client.get(path).get_data(as_text=True)
    panel = html.split('<div class="page-intro">', 1)[1].split("</div>", 1)[0]
    assert f'<h1 id="page-heading">{title}</h1>' in panel
    assert intro in panel
    assert '<dl class="glossary">' not in panel
    assert '<div class="ledger">' not in panel
    assert "page-intro" not in client.get("/").get_data(as_text=True)


def test_studies_pixel_art(client):
    from xml.etree import ElementTree

    html = client.get("/studies").get_data(as_text=True)
    markup = html.split('<svg class="study-art"', 1)[1].split("</svg>", 1)[0]
    symbol = ElementTree.fromstring('<svg class="study-art"' + markup + "</svg>")
    assert symbol.attrib["aria-hidden"] == "true"
    assert symbol.attrib["shape-rendering"] == "crispEdges"
    assert symbol.attrib["viewBox"] == "0 0 64 64"
    assert symbol.attrib["fill"] == "url(#study-cap-fade)"
    assert len(symbol.findall("path")) == 3
    stops = symbol.findall("defs/linearGradient/stop")
    assert len(stops) == 3
    assert stops[-1].attrib["stop-opacity"] == ".1"
    assert html.index('class="study-art"') < html.index('<dl class="glossary">')


def test_resume_header_pixel_art(client):
    from xml.etree import ElementTree

    html = client.get("/cv").get_data(as_text=True)
    markup = html.split('<svg class="study-art"', 1)[1].split("</svg>", 1)[0]
    symbol = ElementTree.fromstring('<svg class="study-art"' + markup + "</svg>")
    assert symbol.attrib["viewBox"] == "0 0 64 64"
    assert symbol.attrib["aria-hidden"] == "true"
    assert symbol.attrib["shape-rendering"] == "crispEdges"
    assert symbol.attrib["fill"] == "url(#resume-art-fade)"
    assert len(symbol.findall("path")) == 2
    assert symbol.find("defs/linearGradient").attrib["id"] == "resume-art-fade"
    assert html.index('class="study-art"') < html.index('<div class="ledger">')


@pytest.mark.parametrize("path, kind", [("/work", "work"), ("/contact", "contact")])
def test_work_and_contact_header_art(client, path, kind):
    from xml.etree import ElementTree

    html = client.get(path).get_data(as_text=True)
    markup = html.split('<svg class="study-art"', 1)[1].split("</svg>", 1)[0]
    symbol = ElementTree.fromstring('<svg class="study-art"' + markup + "</svg>")
    assert symbol.attrib["viewBox"] == "0 0 64 64"
    assert symbol.attrib["aria-hidden"] == "true"
    assert symbol.attrib["shape-rendering"] == "crispEdges"
    assert symbol.attrib["fill"] == f"url(#{kind}-art-fade)"
    assert len(symbol.findall("path")) == 2
    assert symbol.findall("defs/linearGradient/stop")[-1].attrib["stop-opacity"] == ".1"
    if kind == "contact":
        assert 'href="/cv#request">request form</a>' in html
        assert 'href="mailto:drew@dsmorgan.com"' in html
