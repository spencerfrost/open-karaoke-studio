"""song_vocal_range_detail

How each song's vocal range was decided: the method, the label when there's no
sung range (rapped, no lead found, one note), the moments that set each end and
the md5 of the synced lyrics it read. Null until the range is measured.

Revision ID: c8d2f5a1e9b4
Revises: b5e1d8a3c7f2
Create Date: 2026-11-11 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c8d2f5a1e9b4"
down_revision: Union[str, None] = "b5e1d8a3c7f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("songs", sa.Column("vocal_range_detail", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("songs", "vocal_range_detail")
