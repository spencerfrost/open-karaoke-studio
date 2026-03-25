"""add_chords_data_to_songs

Add chords_data JSON column to songs table for chord detection data.

Revision ID: a1b2c3d4e5f6
Revises: 6c0c98ee5860
Create Date: 2026-02-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '6c0c98ee5860'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add chords_data column to songs table."""
    op.add_column('songs', sa.Column('chords_data', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Remove chords_data column from songs table."""
    op.drop_column('songs', 'chords_data')
