# D.S. Morgan portfolio

Flask portfolio with a private admin catalog for papers and projects.
The public site reads like a short book. `/` is the index (title page and
contents); the pages follow in order: `/studies`, `/work`, `/cv`, `/contact`.
The order, titles, and meta descriptions live in `PAGES` in `app/pages.py`;
the contents list, running head, folios, page-turn links, and footer page list
all follow it. Papers and projects are managed through the admin and render as
library catalog cards with an optional summary. Profile text lives in
`app/templates/pages/`. The admin is intentionally not linked from public pages.

## CV requests

The full CV is not downloadable. Visitors submit the form on `/cv` (name,
email, organization, reason; role, phone, and message optional). Each request
is saved to `cv_requests` and emailed to you through Resend with `Reply-To` set
to the requester, so replying sends your CV directly. The requester receives no
automatic copy. Requests appear on the admin dashboard, where you can mark them
handled; requests whose email failed are flagged there.

Spam protection: Cloudflare Turnstile, a hidden honeypot field, and a limit of
three requests per hour per visitor (stored as a salted hash, never a raw IP).
Settings (all optional locally; set them in production):

```sh
FLASK_RESEND_API_KEY=re_...
FLASK_CV_REQUEST_FROM="D.S. Morgan <form@updates.dsmorgan.com>"  # verified Resend domain
FLASK_CV_REQUEST_TO=drew@dsmorgan.com
FLASK_TURNSTILE_SITE_KEY=...
FLASK_TURNSTILE_SECRET_KEY=...
FLASK_TRUST_CF_CONNECTING_IP=true  # only when served behind Cloudflare
```

Without Resend keys, requests are saved only; without Turnstile keys, the
widget and check are skipped. Cloudflare's test keys
(`1x00000000000000000000AA` / `1x0000000000000000000000000000000AA`) always pass.

## Design system

The "reading room" theme is a cream page on a walnut desk with oxblood accents,
set entirely in EB Garamond (self-hosted variable WOFF2, roman and italic, SIL
Open Font License in `app/static/fonts`). No images and no JavaScript; browsers
use their standard cursors. CSS lives in four files, loaded in order:

- `css/tokens.css` - fonts, colors, type scale, spacing. Retheme here only.
- `css/base.css` - desk, page sheet, base typography, mobile and print rules.
- `css/components.css` - ribbon, running head, contents, ornaments, catalog
  cards, ledger, buttons, and forms.
- `css/pages.css` - title page, 404, and admin layouts.

To add a page, add a `Page` to `PAGES`, a route in `app/pages.py`, and a
template that uses the `page_head` macro from `macros.html`. Supporting
browsers cross-fade between pages (disabled for reduced motion). Below 40rem
the desk disappears and the page fills the screen. The favicon is an SVG
monogram at `app/static/favicon.svg`.

## Local development

```sh
uv sync
uv run flask --app app db upgrade
uv run flask --app app create-admin
uv run flask --app app run --debug
```

Configure `DATABASE_URL` with the direct Neon PostgreSQL connection string,
including SSL parameters, and `FLASK_SECRET_KEY` with a generated random key in
an untracked `.env` file. Never commit credentials. The Flask CLI loads `.env`;
other production entry points must receive environment variables from hosting.
The debug server is for local development only.

## Publishing

Sign in at `/admin/login`. The dashboard lists published entries and drafts.
Use **Add entry** or **Edit** to manage title, type, original written date,
public link, optional Version Control URL, and publication status.
Only published entries appear on the homepage. Links must use HTTP or HTTPS.
An unknown written date may be left blank.

Delete opens a confirmation page. Its POST action removes only the catalog
record, never the linked document or source repository. Logout and all changes
require a CSRF token.

## Production

The app runs under gunicorn in a container (`Dockerfile`, `wsgi.py`,
`gunicorn.conf.py`) and listens on `$PORT` (default 8080), as Google Cloud Run
expects. Test the image locally:

```sh
docker build -t dsmorgan-site .
docker run --rm -p 8080:8080 --env-file .env dsmorgan-site
```

Required environment: `FLASK_SECRET_KEY` and `DATABASE_URL`. The app refuses to
start without them. Also set `FLASK_RESEND_API_KEY`, `FLASK_CV_REQUEST_FROM`,
`FLASK_CV_REQUEST_TO`, and the real `FLASK_TURNSTILE_SITE_KEY` /
`FLASK_TURNSTILE_SECRET_KEY` (Turnstile keys only work on their configured
hostnames). Optional: `WEB_CONCURRENCY` and `GUNICORN_THREADS` (defaults 1 and 8),
`FLASK_PROXY_HOPS` (default 1, for Cloud Run's front end), and
`FLASK_TRUST_CF_CONNECTING_IP` (only when traffic is proxied through Cloudflare).

Deploy to Cloud Run (project `dsmorgan-site`, region `us-central1`).
`FLASK_SECRET_KEY`, `DATABASE_URL`, and `FLASK_RESEND_API_KEY` come from
Secret Manager (`flask-secret-key`, `database-url`, `resend-api-key`):

```sh
gcloud run deploy dsmorgan-site --source . --region us-central1 \
  --max-instances=1 --min-instances=0
```

Settings persist between deploys. Emergency stop (blocks public traffic;
undo with `--ingress all`):

```sh
gcloud run services update dsmorgan-site --region us-central1 --ingress internal
```

Cloud Run reserves paths ending in `z`, so the health check is `/health`.

Run migrations from a trusted machine against Neon before deploying code that
needs them: `uv run flask --app app db upgrade`. The container never migrates.

Hardening built in:

- Secure, HttpOnly, SameSite cookies outside debug mode; HTTPS URLs.
- Content Security Policy and related security headers; HSTS over HTTPS only.
- Admin pages are never cached; static files get a `?v=` content hash and a
  one-year cache.
- Admin login locks out an address after 5 failures in 15 minutes.
- `/health`, `/robots.txt`, and `/sitemap.xml` (built from the page registry).

## Checks

```sh
uv run python -m pytest
uv run ruff check app tests
uv run ruff format --check app tests
```

GitHub Actions runs these checks and a Docker build on every push to `main`
and on pull requests.

Tests use an isolated in-memory SQLite database, not Neon. Model changes
still require reviewed Alembic migrations; this editor adds no schema changes.
