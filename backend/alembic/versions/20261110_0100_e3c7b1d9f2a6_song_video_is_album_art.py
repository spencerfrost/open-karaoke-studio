"""song_video_is_album_art

Whether a song's YouTube video is an album track upload, whose picture is the
album cover. Null until the download or the "Album-art videos" job looks.

Revision ID: e3c7b1d9f2a6
Revises: a7d2e9c4b1f8
Create Date: 2026-11-10 01:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e3c7b1d9f2a6"
down_revision: Union[str, None] = "a7d2e9c4b1f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "songs", sa.Column("video_is_album_art", sa.Boolean(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("songs", "video_is_album_art")
