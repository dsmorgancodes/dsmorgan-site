from dataclasses import dataclass

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy.exc import SQLAlchemyError

from app import cv_requests, rate_limit
from app.extension import db
from app.forms import CVRequestForm
from app.models import CVRequest, PortfolioEntry

pages = Blueprint("pages", __name__)


@dataclass(frozen=True)
class Page:
    endpoint: str
    title: str
    description: str


# Reading order of the book. The contents, folios, and page turns follow it.
PAGES = (
    Page(
        "index",
        "Index",
        "Drew M. Schaffner, M.S. Mathematics: papers, projects, and graduate study "
        "in mathematics, data science, and artificial intelligence.",
    ),
    Page(
        "studies",
        "Areas of Study",
        "Graduate disciplines: artificial intelligence, group theory, data science, "
        "linear algebra, real analysis, graph theory, and topology.",
    ),
    Page(
        "work",
        "Selected Work",
        "Papers, coursework, and projects by Drew M. Schaffner.",
    ),
    Page(
        "cv",
        "Curriculum Vitae",
        "Education and positions of Drew M. Schaffner, with a form to request "
        "the full CV.",
    ),
    Page(
        "contact",
        "Correspondence",
        "Contact Drew M. Schaffner by email or through professional profiles.",
    ),
)


@pages.app_context_processor
def book_context():
    endpoint = request.endpoint or ""
    position = next(
        (i for i, page in enumerate(PAGES) if f"pages.{page.endpoint}" == endpoint),
        None,
    )
    context = {
        "book_pages": PAGES,
        "current_page": None,
        "folio": None,
        "previous_page": None,
        "next_page": None,
    }
    if position is not None:
        context.update(
            current_page=PAGES[position],
            folio=position,
            previous_page=PAGES[position - 1] if position > 0 else None,
            next_page=PAGES[position + 1] if position + 1 < len(PAGES) else None,
        )
    return context


@pages.get("/")
def index():
    return render_template("pages/index.html")


@pages.get("/studies")
def studies():
    return render_template("pages/studies.html")


@pages.get("/work")
def work():
    statement = (
        db.select(PortfolioEntry)
        .where(PortfolioEntry.published.is_(True))
        .order_by(
            PortfolioEntry.written_date.desc().nulls_last(),
            PortfolioEntry.id.desc(),
        )
    )
    entries = db.session.execute(statement).scalars().all()
    return render_template("pages/work.html", entries=entries)


@pages.route("/cv", methods=["GET", "POST"])
def cv():
    form = CVRequestForm()
    site_key = current_app.config.get("TURNSTILE_SITE_KEY")

    if form.validate_on_submit():
        if form.website.data:
            # Bots get the same response as people, but nothing is stored.
            return redirect(url_for("pages.cv_requested"))

        fingerprint = rate_limit.client_hash()
        if cv_requests.rate_limited(fingerprint):
            flash("Too many requests. Please try again in an hour.", "error")
            return render_template("pages/cv.html", form=form, site_key=site_key), 429

        if not cv_requests.verify_turnstile(request.form.get("cf-turnstile-response")):
            flash("Please complete the verification and try again.", "error")
            return render_template("pages/cv.html", form=form, site_key=site_key), 400

        cv_request = CVRequest(client_hash=fingerprint)
        form.populate_obj(cv_request)
        cv_request.phone = cv_request.phone or None
        cv_request.role = cv_request.role or None
        cv_request.message = cv_request.message or None
        db.session.add(cv_request)
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Could not save a CV request")
            flash("Your request could not be saved. Please try again.", "error")
            return render_template("pages/cv.html", form=form, site_key=site_key), 503

        cv_request.notified = cv_requests.send_notification(cv_request)
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Could not record CV notification status")

        return redirect(url_for("pages.cv_requested"))

    status = 400 if form.errors else 200
    return render_template("pages/cv.html", form=form, site_key=site_key), status


@pages.get("/cv/requested")
def cv_requested():
    return render_template("pages/cv_requested.html")


@pages.get("/contact")
def contact():
    return render_template("pages/contact.html")


@pages.get("/robots.txt")
def robots():
    site = current_app.config["SITE_URL"]
    body = f"User-agent: *\nDisallow: /admin\n\nSitemap: {site}/sitemap.xml\n"
    return Response(body, mimetype="text/plain")


@pages.get("/sitemap.xml")
def sitemap():
    site = current_app.config["SITE_URL"]
    urls = "".join(
        f"  <url><loc>{site}{url_for(f'pages.{page.endpoint}')}</loc></url>\n"
        for page in PAGES
    )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}</urlset>\n"
    )
    return Response(body, mimetype="application/xml")


@pages.get("/healthz")
def healthz():
    return {"status": "ok"}


@pages.get("/favicon.ico")
def favicon():
    return redirect(url_for("static", filename="favicon.svg"), code=301)
