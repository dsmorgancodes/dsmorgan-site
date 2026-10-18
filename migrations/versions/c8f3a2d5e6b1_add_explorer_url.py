"""Add optional interactive explorer links.

Revision ID: c8f3a2d5e6b1
Revises: b7e2a1c4d9f0
"""

import sqlalchemy as sa
from alembic import op

revision = "c8f3a2d5e6b1"
down_revision = "b7e2a1c4d9f0"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("portfolio_entries") as batch_op:
        batch_op.add_column(sa.Column("explorer_url", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("portfolio_entries") as batch_op:
        batch_op.drop_column("explorer_url")
