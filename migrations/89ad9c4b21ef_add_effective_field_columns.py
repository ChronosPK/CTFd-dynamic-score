"""Add effective field columns

Revision ID: 89ad9c4b21ef
Revises: 6f4a8b9c2d10
Create Date: 2026-05-27
"""

import sqlalchemy as sa

from CTFd.plugins.migrations import get_columns_for_table

revision = "89ad9c4b21ef"
down_revision = "6f4a8b9c2d10"
branch_labels = None
depends_on = None


def upgrade(op=None):
    columns = get_columns_for_table(
        op=op, table_name="dynamic_score_state", names_only=True
    )

    if "reference_active_accounts" not in columns:
        op.add_column(
            "dynamic_score_state",
            sa.Column("reference_active_accounts", sa.Integer(), nullable=True),
        )

    if "effective_field" not in columns:
        op.add_column(
            "dynamic_score_state",
            sa.Column("effective_field", sa.Integer(), nullable=True),
        )

    conn = op.get_bind()
    url = str(conn.engine.url)
    if url.startswith("postgres"):
        conn.execute(
            """
            UPDATE dynamic_score_state
            SET reference_active_accounts = COALESCE(reference_active_accounts, reference_accounts),
                effective_field = COALESCE(effective_field, reference_accounts)
            """
        )
    else:
        conn.execute(
            """
            UPDATE dynamic_score_state
            SET `reference_active_accounts` = COALESCE(`reference_active_accounts`, `reference_accounts`),
                `effective_field` = COALESCE(`effective_field`, `reference_accounts`)
            """
        )


def downgrade(op=None):
    columns = get_columns_for_table(
        op=op, table_name="dynamic_score_state", names_only=True
    )

    if "effective_field" in columns:
        op.drop_column("dynamic_score_state", "effective_field")

    if "reference_active_accounts" in columns:
        op.drop_column("dynamic_score_state", "reference_active_accounts")
