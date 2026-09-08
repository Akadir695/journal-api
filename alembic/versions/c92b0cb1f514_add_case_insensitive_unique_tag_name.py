"""add case insensitive unique tag name

Revision ID: c92b0cb1f514
Revises: 78dcd878ceca
Create Date: 2026-08-22 19:13:50.560050

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c92b0cb1f514"
down_revision: str | Sequence[str] | None = "78dcd878ceca"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "uq_tags_user_lower_name",
        "tags",
        ["user_id", sa.text("lower(name)")],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_tags_user_lower_name", table_name="tags")
