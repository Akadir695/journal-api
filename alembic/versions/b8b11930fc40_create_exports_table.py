"""create exports table

Revision ID: b8b11930fc40
Revises: 7a2dd6a096ac
Create Date: 2026-09-01 20:16:53.806356

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8b11930fc40"
down_revision: str | Sequence[str] | None = "7a2dd6a096ac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_exports_user_id"), "exports", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_exports_user_id"), table_name="exports")
    op.drop_table("exports")
