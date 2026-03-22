"""add_albums_table_and_song_fks

Revision ID: a3b4c5d6e7f8
Revises: bc35cdb6192a
Create Date: 2026-03-22 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, None] = "bc35cdb6192a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create albums table
    op.create_table(
        "albums",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("artist_id", sa.Integer(), nullable=True),
        sa.Column("itunes_collection_id", sa.Integer(), nullable=True),
        sa.Column("release_date", sa.String(), nullable=True),
        sa.Column("cover_path", sa.String(), nullable=True),
        sa.Column(
            "image_status",
            sa.String(),
            nullable=False,
            server_default="not_checked",
        ),
        sa.ForeignKeyConstraint(
            ["artist_id"],
            ["artists.id"],
            name="fk_albums_artist_id_artists",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("itunes_collection_id"),
    )

    # 2. Add FK columns to songs (nullable, no server default needed)
    op.add_column("songs", sa.Column("artist_id", sa.Integer(), nullable=True))
    op.add_column("songs", sa.Column("album_id", sa.Integer(), nullable=True))

    # 3. Backfill artists: upsert Artist records from existing song.artist strings
    op.execute("""
        INSERT INTO artists (name, image_status)
        SELECT DISTINCT lower(trim(artist)), 'not_checked'
        FROM songs
        WHERE artist IS NOT NULL AND trim(artist) != ''
        ON CONFLICT (name) DO NOTHING
    """)

    # 4. Backfill songs.artist_id
    op.execute("""
        UPDATE songs
        SET artist_id = artists.id
        FROM artists
        WHERE lower(trim(songs.artist)) = artists.name
    """)

    # 5. Backfill albums: one record per unique (artist_id, album title) combo
    op.execute("""
        INSERT INTO albums (title, artist_id, image_status)
        SELECT DISTINCT songs.album, songs.artist_id, 'not_checked'
        FROM songs
        WHERE songs.album IS NOT NULL
          AND trim(songs.album) != ''
          AND songs.artist_id IS NOT NULL
    """)

    # 6. Backfill songs.album_id
    op.execute("""
        UPDATE songs
        SET album_id = albums.id
        FROM albums
        WHERE songs.album = albums.title
          AND songs.artist_id = albums.artist_id
    """)

    # 7. Add FK constraints after data is backfilled
    op.create_foreign_key(
        "fk_songs_artist_id_artists", "songs", "artists", ["artist_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_songs_album_id_albums", "songs", "albums", ["album_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_songs_album_id_albums", "songs", type_="foreignkey")
    op.drop_constraint("fk_songs_artist_id_artists", "songs", type_="foreignkey")
    op.drop_column("songs", "album_id")
    op.drop_column("songs", "artist_id")
    op.drop_table("albums")
