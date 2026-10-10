"""album sources

Albums come from YouTube Music (the album of the exact video downloaded) or
Deezer instead of iTunes, so an album is keyed by (source, source_id). Existing
iTunes albums keep their id as source 'itunes'; the albums the March migration
made from songs.album have no source and get relinked by the album job.

Songs gain album_hand_set_at (a person set the album name; automatic runs skip
the song) and album_checked_at (the lookup found no cover). The explicit flag
is no longer iTunes', and the iTunes track id and preview url go: nothing
reads them.

Revision ID: c5f8a2e7d394
Revises: b7c4e2d9a816
Create Date: 2026-10-10 01:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c5f8a2e7d394"
down_revision: Union[str, None] = "b7c4e2d9a816"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("albums", sa.Column("source", sa.String(), nullable=True))
    op.add_column("albums", sa.Column("source_id", sa.String(), nullable=True))
    op.execute("""
        UPDATE albums
        SET source = 'itunes', source_id = CAST(itunes_collection_id AS VARCHAR)
        WHERE itunes_collection_id IS NOT NULL
        """)
    op.create_unique_constraint(
        "uq_albums_source_source_id", "albums", ["source", "source_id"]
    )
    op.drop_column("albums", "itunes_collection_id")

    op.add_column("songs", sa.Column("album_hand_set_at", sa.DateTime(), nullable=True))
    op.add_column("songs", sa.Column("album_checked_at", sa.DateTime(), nullable=True))
    op.alter_column("songs", "itunes_explicit", new_column_name="explicit")
    op.drop_column("songs", "itunes_track_id")
    op.drop_column("songs", "itunes_preview_url")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("songs", sa.Column("itunes_preview_url", sa.String(), nullable=True))
    op.add_column("songs", sa.Column("itunes_track_id", sa.Integer(), nullable=True))
    op.alter_column("songs", "explicit", new_column_name="itunes_explicit")
    op.drop_column("songs", "album_checked_at")
    op.drop_column("songs", "album_hand_set_at")

    op.add_column(
        "albums", sa.Column("itunes_collection_id", sa.Integer(), nullable=True)
    )
    op.execute("""
        UPDATE albums SET itunes_collection_id = CAST(source_id AS INTEGER)
        WHERE source = 'itunes'
        """)
    op.create_unique_constraint(
        "albums_itunes_collection_id_key", "albums", ["itunes_collection_id"]
    )
    op.drop_constraint("uq_albums_source_source_id", "albums", type_="unique")
    op.drop_column("albums", "source_id")
    op.drop_column("albums", "source")
