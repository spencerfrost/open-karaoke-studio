"""add_bpm_field_to_songs

Revision ID: ff709dcf3edf
Revises: ba1f2fcfe4d4
Create Date: 2025-12-09 23:24:46.342087

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff709dcf3edf'
down_revision: Union[str, None] = 'ba1f2fcfe4d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add BPM column to songs table
    op.add_column('songs', sa.Column('bpm', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove BPM column from songs table
    op.drop_column('songs', 'bpm')
