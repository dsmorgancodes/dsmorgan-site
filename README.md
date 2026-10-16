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

The research-terminal layout uses system monospace headings and navigation
with system sans-serif body text, standard cursors, and three
Rosé Pine variants: Rosé Pine (dark), Moon (dim), and Dawn (light).
The rose-shaped light/dark control in the header opens a keyboard-accessible
radio picker. The initial appearance follows the system light/dark preference;
an explicit choice is saved in localStorage and applies across pages and tabs.
If storage is unavailable the choice still works for the current page, with a
console warning. Without JavaScript the site remains readable in dark Rosé Pine.
There are no shell prompts, filesystem-style navigation, typing animations,
or simulated command input. The homepage leads with an introduction and links
to work and contact, followed by a labeled Education panel with both degrees
and a CV link. The Explore workbench groups Studies, Selected Work, and
Collaboration into bordered panels. Degrees and study/work panels sit side by
side on desktop and stack on mobile. Work uses editorial
listings with type and date, rather than library cards and call numbers.

CSS is loaded in this order:

- `css/tokens.css` - fonts, colors, type scale, spacing. Retheme here only.
- `css/base.css` - desk, page sheet, base typography, mobile and print rules.
- `css/components.css` - ribbon, running head, contents, ornaments, catalog
  cards, ledger, buttons, and forms.
- `css/pages.css` - title page, 404, and admin layouts.
- `css/terminal.css` - active terminal palette, typography, layout overrides,
  responsive navigation, and theme picker. Edit the active theme here.

`js/theme.js` applies the theme before styles load to avoid a flash, and handles
preference persistence. It is self-hosted and works with the existing CSP.
Palette values derive from https://rosepinetheme.com/palette/ with contrast
adjustments for secondary text and Dawn accents. Turnstile follows the system
theme independently and uses its flexible-width widget.

To add a page, add a `Page` to `PAGES`, a route in `app/pages.py`, and a
template that uses the `page_head` macro from `macros.html`. Supporting
browsers cross-fade between pages (disabled for reduced motion). Navigation
wraps on small screens; the content remains a single readable column.
Legacy book-style components remain in the base styles, with their appearance
overridden by the terminal layer. The favicon is an SVG
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
and on pull requests. After both jobs pass, pushes to `main` also build and
publish a commit-tagged image to Artifact Registry, deploy it to Cloud Run, and
check `/health`. Pull requests never deploy. Deployments run one at a time;
existing environment variables, secret references, and instance limits are
preserved. No manual deploy command is needed for normal updates.

Deployment uses Workload Identity Federation, not a stored Google key.
The `github-actions` pool and `dsmorgan-site` provider in project
`dsmorgan-site` trust only push events on `main` from this repository's numeric
GitHub repository and owner IDs. The `github-deploy` service account can write
to the `cloud-run-source-deploy` Artifact Registry repository, update this
Cloud Run service, and act as its existing runtime service account. It has no
direct Secret Manager access.

Watch deployment status in GitHub's **Actions** tab or with `gh run list`.
If checks fail, the current live revision stays unchanged. A failed post-deploy
health check marks the workflow failed but does not automatically roll back;
use Cloud Run's revision traffic controls if a rollback is needed.
Schema migrations still need to run before pushing code that requires them.

Tests use an isolated in-memory SQLite database, not Neon. Model changes
still require reviewed Alembic migrations; this editor adds no schema changes.
