"""add search vector to entries

Revision ID: 7a2dd6a096ac
Revises: c92b0cb1f514
Create Date: 2026-08-24 12:21:57.109161

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a2dd6a096ac'
down_revision: Union[str, Sequence[str], None] = 'c92b0cb1f514'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        ALTER TABLE entries
        ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, ''))
        ) STORED
    """)
    op.execute("CREATE INDEX ix_entries_search_vector ON entries USING GIN (search_vector)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_entries_search_vector")
    op.execute("ALTER TABLE entries DROP COLUMN search_vector")
