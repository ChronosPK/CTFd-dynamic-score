"""Create dynamic score state

Revision ID: 6f4a8b9c2d10
Revises: 5d57f1824c51
Create Date: 2026-05-27
"""

import sqlalchemy as sa

from CTFd.plugins.migrations import get_all_tables

revision = "6f4a8b9c2d10"
down_revision = "5d57f1824c51"
branch_labels = None
depends_on = None


def upgrade(op=None):
    tables = get_all_tables(op=op)
    if "dynamic_score_state" in tables:
        return

    op.create_table(
        "dynamic_score_state",
        sa.Column(
            "challenge_id",
            sa.Integer(),
            sa.ForeignKey("challenges.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("reference_accounts", sa.Integer(), nullable=False),
        sa.Column("reference_challenges", sa.Integer(), nullable=False),
        sa.Column("target_solves", sa.Float(), nullable=False),
    )


def downgrade(op=None):
    tables = get_all_tables(op=op)
    if "dynamic_score_state" not in tables:
        return

    op.drop_table("dynamic_score_state")
