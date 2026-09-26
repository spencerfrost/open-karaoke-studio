"""remove_bpm_from_songs

Revision ID: a2445e5aca5e
Revises: 20260407_1300_add_song_status
Create Date: 2026-04-08 09:57:55.178846

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2445e5aca5e'
down_revision: Union[str, None] = '20260407_1300_add_song_status'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('songs', 'bpm')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('songs', sa.Column('bpm', sa.Float(), nullable=True))
