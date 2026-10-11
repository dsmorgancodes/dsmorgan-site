from datetime import UTC, date, datetime

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import check_password_hash, generate_password_hash

from app.extension import db


class PortfolioEntry(db.Model):
    __tablename__ = "portfolio_entries"
    __table_args__ = (
        CheckConstraint(
            "entry_type IN ('paper', 'project')",
            name="ck_portfolio_entries_entry_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    written_date: Mapped[date | None] = mapped_column(nullable=True)
    link: Mapped[str] = mapped_column(Text, nullable=False)
    version_control_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    published: Mapped[bool] = mapped_column(default=False, nullable=False)


class AdminUser(UserMixin, db.Model):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class CVRequest(db.Model):
    __tablename__ = "cv_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    organization: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    notified: Mapped[bool] = mapped_column(default=False, nullable=False)
    handled: Mapped[bool] = mapped_column(default=False, nullable=False)


class RateLimitEvent(db.Model):
    __tablename__ = "rate_limit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    client_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        db.Index("ix_rate_limit_events_kind_client", "kind", "client_hash"),
    )
