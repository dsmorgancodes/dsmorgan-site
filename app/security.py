import hashlib
import os
from functools import lru_cache

from flask import current_app, request

TURNSTILE = "https://challenges.cloudflare.com"

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        f"script-src 'self' {TURNSTILE}",
        f"frame-src {TURNSTILE}",
        f"connect-src 'self' {TURNSTILE}",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), browsing-topics=()",
}


@lru_cache(maxsize=256)
def file_digest(path, mtime_ns):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()[:10]


def static_version(filename):
    path = os.path.join(current_app.static_folder or "", filename)
    try:
        return file_digest(path, os.stat(path).st_mtime_ns)
    except OSError:
        return None


def register_security(app):
    @app.url_defaults
    def version_static_urls(endpoint, values):
        if endpoint == "static" and "filename" in values and "v" not in values:
            version = static_version(values["filename"])
            if version:
                values["v"] = version

    @app.after_request
    def add_security_headers(response):
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if request.is_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        if request.blueprint == "admin":
            response.headers["Cache-Control"] = "no-store"
        return response
