"""Add entry summaries and CV requests

Revision ID: 9c1d2e3f4a5b
Revises: 44442eb773a8
Create Date: 2026-10-10 21:10:00

"""
import sqlalchemy as sa
from alembic import op

revision = "9c1d2e3f4a5b"
down_revision = "44442eb773a8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("portfolio_entries") as batch_op:
        batch_op.add_column(sa.Column("summary", sa.Text(), nullable=True))

    op.create_table(
        "cv_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("organization", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=120), nullable=True),
        sa.Column("reason", sa.String(length=40), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("client_hash", sa.String(length=64), nullable=False),
        sa.Column("notified", sa.Boolean(), nullable=False),
        sa.Column("handled", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cv_requests_created_at", "cv_requests", ["created_at"])
    op.create_index("ix_cv_requests_client_hash", "cv_requests", ["client_hash"])


def downgrade():
    op.drop_index("ix_cv_requests_client_hash", table_name="cv_requests")
    op.drop_index("ix_cv_requests_created_at", table_name="cv_requests")
    op.drop_table("cv_requests")
    with op.batch_alter_table("portfolio_entries") as batch_op:
        batch_op.drop_column("summary")
