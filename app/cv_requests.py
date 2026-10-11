import hashlib
import json
from datetime import UTC, datetime, timedelta
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import current_app, request

from app.extension import db
from app.forms import CV_REQUEST_REASONS
from app.models import CVRequest

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
RESEND_URL = "https://api.resend.com/emails"
USER_AGENT = "dsmorgan-site/1.0"


def client_ip():
    if current_app.config.get("TRUST_CF_CONNECTING_IP"):
        forwarded = request.headers.get("CF-Connecting-IP")
        if forwarded:
            return forwarded
    return request.remote_addr or "unknown"


def client_hash():
    secret = current_app.config["SECRET_KEY"]
    return hashlib.sha256(f"{secret}:{client_ip()}".encode()).hexdigest()


def rate_limited(fingerprint):
    limit = int(current_app.config.get("CV_REQUEST_LIMIT_PER_HOUR", 3))
    cutoff = datetime.now(UTC) - timedelta(hours=1)
    recent = db.session.scalar(
        db.select(db.func.count(CVRequest.id)).where(
            CVRequest.client_hash == fingerprint, CVRequest.created_at >= cutoff
        )
    )
    return recent >= limit


def post(url, data, headers):
    req = Request(url, data=data, headers={"User-Agent": USER_AGENT, **headers})
    with urlopen(req, timeout=10) as response:
        return json.loads(response.read() or b"{}")


def verify_turnstile(token):
    secret = current_app.config.get("TURNSTILE_SECRET_KEY")
    if not secret:
        current_app.logger.warning("Turnstile is not configured; skipping check.")
        return True
    if not token:
        return False
    payload = urlencode(
        {"secret": secret, "response": token, "remoteip": client_ip()}
    ).encode()
    try:
        result = post(
            TURNSTILE_VERIFY_URL,
            payload,
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
    except (URLError, TimeoutError, ValueError):
        current_app.logger.exception("Turnstile verification failed")
        return False
    return bool(result.get("success"))


def notification_text(cv_request):
    reasons = dict(CV_REQUEST_REASONS)
    lines = [
        "A visitor requested your CV.",
        "",
        f"Name:         {cv_request.name}",
        f"Email:        {cv_request.email}",
        f"Phone:        {cv_request.phone or '-'}",
        f"Organization: {cv_request.organization}",
        f"Role:         {cv_request.role or '-'}",
        f"Reason:       {reasons.get(cv_request.reason, cv_request.reason)}",
        "",
        "Message:",
        cv_request.message or "-",
        "",
        "Reply to this email to send the CV. The request is also saved in the",
        "admin dashboard.",
    ]
    return "\n".join(lines)


def send_notification(cv_request):
    api_key = current_app.config.get("RESEND_API_KEY")
    if not api_key:
        current_app.logger.warning("Resend is not configured; request saved only.")
        return False
    payload = {
        "from": current_app.config.get(
            "CV_REQUEST_FROM", "D.S. Morgan <form@updates.dsmorgan.com>"
        ),
        "to": [current_app.config.get("CV_REQUEST_TO", "drew@dsmorgan.com")],
        "reply_to": cv_request.email,
        "subject": f"CV request from {cv_request.name} ({cv_request.organization})",
        "text": notification_text(cv_request),
    }
    try:
        post(
            RESEND_URL,
            json.dumps(payload).encode(),
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
    except (URLError, TimeoutError, ValueError):
        current_app.logger.exception("Could not send CV request notification")
        return False
    return True
