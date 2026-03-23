"""remove_dead_artwork_columns

Revision ID: f0a1b2c3d4e5
Revises: e5f6a7b8c9d0
Create Date: 2026-03-23 16:00:00.000000

Remove itunes_artwork_urls and youtube_thumbnail_urls from the songs table.
These columns were never used for display — album art is served via the
albums.cover_path / /api/albums/{id}/cover path, and per-song YouTube
thumbnails are downloaded to disk (songs.thumbnail_path).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "f0a1b2c3d4e5"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop itunes_artwork_urls and youtube_thumbnail_urls from songs."""
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {col["name"] for col in inspector.get_columns("songs")}

    if "itunes_artwork_urls" in existing:
        op.drop_column("songs", "itunes_artwork_urls")

    if "youtube_thumbnail_urls" in existing:
        op.drop_column("songs", "youtube_thumbnail_urls")


def downgrade() -> None:
    """Restore itunes_artwork_urls and youtube_thumbnail_urls to songs."""
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {col["name"] for col in inspector.get_columns("songs")}

    if "youtube_thumbnail_urls" not in existing:
        op.add_column(
            "songs", sa.Column("youtube_thumbnail_urls", sa.Text(), nullable=True)
        )

    if "itunes_artwork_urls" not in existing:
        op.add_column(
            "songs", sa.Column("itunes_artwork_urls", sa.Text(), nullable=True)
        )
