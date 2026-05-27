"""Create dynamic score snapshots

Revision ID: 5d57f1824c51
Revises:
Create Date: 2026-05-27
"""

import sqlalchemy as sa

from CTFd.plugins.migrations import get_all_tables

revision = "5d57f1824c51"
down_revision = None
branch_labels = None
depends_on = None


def upgrade(op=None):
    tables = get_all_tables(op=op)
    if "dynamic_score_snapshot" in tables:
        return

    op.create_table(
        "dynamic_score_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "challenge_id",
            sa.Integer(),
            sa.ForeignKey("challenges.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "solve_id",
            sa.Integer(),
            sa.ForeignKey("solves.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "award_id",
            sa.Integer(),
            sa.ForeignKey("awards.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("score_awarded", sa.Integer(), nullable=False),
    )
    op.create_index(
        "ix_dynamic_score_snapshot_challenge_id",
        "dynamic_score_snapshot",
        ["challenge_id"],
    )


def downgrade(op=None):
    tables = get_all_tables(op=op)
    if "dynamic_score_snapshot" not in tables:
        return

    try:
        op.drop_index(
            "ix_dynamic_score_snapshot_challenge_id",
            table_name="dynamic_score_snapshot",
        )
    except Exception:
        pass

    op.drop_table("dynamic_score_snapshot")
