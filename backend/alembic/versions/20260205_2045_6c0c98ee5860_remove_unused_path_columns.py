"""remove_unused_path_columns

Remove vocals_path, instrumental_path, and original_path columns from songs table.
These paths are deterministic and were never read from the database.

Revision ID: 6c0c98ee5860
Revises: fce8f2d80557
Create Date: 2026-02-05 20:45:43.885507

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '6c0c98ee5860'
down_revision: Union[str, None] = 'fce8f2d80557'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop unused path columns from songs table."""
    op.drop_column('songs', 'vocals_path')
    op.drop_column('songs', 'instrumental_path')
    op.drop_column('songs', 'original_path')


def downgrade() -> None:
    """Re-add path columns to songs table."""
    op.add_column('songs', sa.Column('vocals_path', sa.TEXT(), nullable=True))
    op.add_column('songs', sa.Column('instrumental_path', sa.TEXT(), nullable=True))
    op.add_column('songs', sa.Column('original_path', sa.TEXT(), nullable=True))
