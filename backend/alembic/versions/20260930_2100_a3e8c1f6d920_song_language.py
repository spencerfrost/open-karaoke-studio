"""song_language

The language a song is sung in, as a Whisper language code ("en", "fr").
Lyrics alignment and ASR use it to pick their models; before this every song
was aligned with the English model. Empty means "not known yet": the lyrics
task detects it from the vocals and stores it.

Revision ID: a3e8c1f6d920
Revises: f5b9d2c7e184
Create Date: 2026-09-30 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3e8c1f6d920'
down_revision: Union[str, None] = 'f5b9d2c7e184'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('songs', sa.Column('language', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('songs', 'language')
