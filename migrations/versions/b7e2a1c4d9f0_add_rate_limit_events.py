"""Add rate limit events

Revision ID: b7e2a1c4d9f0
Revises: 9c1d2e3f4a5b
Create Date: 2026-10-11 03:55:00

"""
import sqlalchemy as sa
from alembic import op

revision = "b7e2a1c4d9f0"
down_revision = "9c1d2e3f4a5b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rate_limit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("client_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rate_limit_events_created_at", "rate_limit_events", ["created_at"]
    )
    op.create_index(
        "ix_rate_limit_events_kind_client",
        "rate_limit_events",
        ["kind", "client_hash"],
    )


def downgrade():
    op.drop_index("ix_rate_limit_events_kind_client", table_name="rate_limit_events")
    op.drop_index("ix_rate_limit_events_created_at", table_name="rate_limit_events")
    op.drop_table("rate_limit_events")
