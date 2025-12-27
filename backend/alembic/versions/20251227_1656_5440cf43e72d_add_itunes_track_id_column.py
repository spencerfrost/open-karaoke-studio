"""add_itunes_track_id_column

Revision ID: 5440cf43e72d
Revises: 6dd07e747f45
Create Date: 2025-12-27 16:56:28.391198

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5440cf43e72d'
down_revision: Union[str, None] = '6dd07e747f45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add itunes_track_id column to songs table
    op.add_column('songs', sa.Column('itunes_track_id', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove itunes_track_id column from songs table
    op.drop_column('songs', 'itunes_track_id')
