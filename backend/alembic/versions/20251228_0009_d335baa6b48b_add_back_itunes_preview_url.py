"""add_back_itunes_preview_url

Revision ID: d335baa6b48b
Revises: 9fc494c886d6
Create Date: 2025-12-28 00:09:20.863601

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd335baa6b48b'
down_revision: Union[str, None] = '9fc494c886d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add back itunes_preview_url column that was accidentally dropped."""
    # Note: Column may already exist from manual ALTER TABLE fix.
    # Using batch_alter_table for SQLite compatibility.
    from sqlalchemy import inspect
    from alembic import op

    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('songs')]

    if 'itunes_preview_url' not in columns:
        op.add_column('songs', sa.Column('itunes_preview_url', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove itunes_preview_url column."""
    op.drop_column('songs', 'itunes_preview_url')
