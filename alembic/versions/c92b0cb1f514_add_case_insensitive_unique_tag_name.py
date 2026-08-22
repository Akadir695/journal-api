"""add case insensitive unique tag name

Revision ID: c92b0cb1f514
Revises: 78dcd878ceca
Create Date: 2026-08-22 19:13:50.560050

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c92b0cb1f514'
down_revision: Union[str, Sequence[str], None] = '78dcd878ceca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
