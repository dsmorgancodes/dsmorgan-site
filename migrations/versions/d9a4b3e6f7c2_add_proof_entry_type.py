"""Allow proofs in the portfolio catalog.

Revision ID: d9a4b3e6f7c2
Revises: c8f3a2d5e6b1
"""

import sqlalchemy as sa
from alembic import op

revision = "d9a4b3e6f7c2"
down_revision = "c8f3a2d5e6b1"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("portfolio_entries") as batch_op:
        batch_op.drop_constraint("ck_portfolio_entries_entry_type", type_="check")
        batch_op.create_check_constraint(
            "ck_portfolio_entries_entry_type",
            "entry_type IN ('paper', 'project', 'proof')",
        )


def downgrade():
    proofs = (
        op.get_bind()
        .execute(
            sa.text("SELECT count(*) FROM portfolio_entries WHERE entry_type = 'proof'")
        )
        .scalar_one()
    )
    if proofs:
        raise RuntimeError(
            "Reclassify proof entries as papers or projects before downgrading."
        )
    with op.batch_alter_table("portfolio_entries") as batch_op:
        batch_op.drop_constraint("ck_portfolio_entries_entry_type", type_="check")
        batch_op.create_check_constraint(
            "ck_portfolio_entries_entry_type",
            "entry_type IN ('paper', 'project')",
        )
