"""song_lrc_offset_sweep

Each song's LRC offset sweep, stored as a layer: how well the lyrics align at
every whole-song shift tried, and the shift that passes the gate, waiting to
be applied after a listen. Null until the "LRC offset sweep" job sweeps it.

Revision ID: b5e1d8a3c7f2
Revises: f4a8c2e6b1d3
Create Date: 2026-11-11 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b5e1d8a3c7f2"
down_revision: Union[str, None] = "f4a8c2e6b1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("songs", sa.Column("lrc_offset_sweep", sa.Text(), nullable=True))
    op.add_column("songs", sa.Column("lrc_offset_version", sa.Integer(), nullable=True))
    op.add_column(
        "songs", sa.Column("lrc_offset_lrc_md5", sa.String(length=32), nullable=True)
    )
    op.add_column(
        "songs", sa.Column("lrc_offset_pending_shift", sa.Float(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("songs", "lrc_offset_pending_shift")
    op.drop_column("songs", "lrc_offset_lrc_md5")
    op.drop_column("songs", "lrc_offset_version")
    op.drop_column("songs", "lrc_offset_sweep")
