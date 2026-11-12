"""loudness_lufs

Loudness is now measured as EBU R128 integrated loudness with a true peak,
on the stems the player plays by default. The old RMS dBFS values are a
different unit, so they are dropped rather than renamed. gain_db keeps its
old values until each song is re-measured.

Revision ID: d8a3f5b2c71e
Revises: c4f2a7e1b903
Create Date: 2026-10-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8a3f5b2c71e'
down_revision: Union[str, None] = 'c4f2a7e1b903'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('songs', sa.Column('loudness_lufs', sa.Float(), nullable=True))
    op.add_column('songs', sa.Column('true_peak_dbtp', sa.Float(), nullable=True))
    op.drop_column('songs', 'loudness_dbfs')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('songs', sa.Column('loudness_dbfs', sa.Float(), nullable=True))
    op.drop_column('songs', 'true_peak_dbtp')
    op.drop_column('songs', 'loudness_lufs')
