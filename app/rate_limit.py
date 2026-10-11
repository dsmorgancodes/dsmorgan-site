import hashlib
from datetime import UTC, datetime, timedelta

from flask import current_app, request

from app.extension import db
from app.models import RateLimitEvent


def client_ip():
    if current_app.config.get("TRUST_CF_CONNECTING_IP"):
        forwarded = request.headers.get("CF-Connecting-IP")
        if forwarded:
            return forwarded
    return request.remote_addr or "unknown"


def client_hash():
    """A salted hash, so raw visitor IP addresses are never stored."""
    secret = current_app.config["SECRET_KEY"]
    return hashlib.sha256(f"{secret}:{client_ip()}".encode()).hexdigest()


def recent_events(kind, fingerprint, window):
    cutoff = datetime.now(UTC) - window
    return db.session.scalar(
        db.select(db.func.count(RateLimitEvent.id)).where(
            RateLimitEvent.kind == kind,
            RateLimitEvent.client_hash == fingerprint,
            RateLimitEvent.created_at >= cutoff,
        )
    )


def record_event(kind, fingerprint):
    db.session.execute(
        db.delete(RateLimitEvent).where(
            RateLimitEvent.created_at < datetime.now(UTC) - timedelta(days=1)
        )
    )
    db.session.add(RateLimitEvent(kind=kind, client_hash=fingerprint))
    db.session.commit()


def clear_events(kind, fingerprint):
    db.session.execute(
        db.delete(RateLimitEvent).where(
            RateLimitEvent.kind == kind, RateLimitEvent.client_hash == fingerprint
        )
    )
    db.session.commit()
