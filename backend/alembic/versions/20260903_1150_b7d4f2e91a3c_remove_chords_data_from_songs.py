"""remove_chords_data_from_songs

Guitar chord detection is removed. The detector matched beat-synced chroma
against 24 major/minor triad templates with no smoothing, so it emitted a
change on every beat the match flipped — around 62 changes per minute, several
times the real rate. The stored progressions are noise, so the column goes with
the feature rather than being kept for a future re-detection.

Revision ID: b7d4f2e91a3c
Revises: c4e7a95d31b8
Create Date: 2026-09-03 11:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision: str = 'b7d4f2e91a3c'
down_revision: Union[str, None] = 'c4e7a95d31b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('songs', 'chords_data')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('songs', sa.Column('chords_data', JSON(), nullable=True))
