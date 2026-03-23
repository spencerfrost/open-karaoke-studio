"""add_song_artists_and_display_name

Revision ID: d4e5f6a7b8c9
Revises: c6683db9eb12
Create Date: 2026-03-23 14:00:00.000000

"""
import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c6683db9eb12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Regex patterns (mirrors app.services.artist_parsing)
_FEAT_PATTERN = re.compile(r"\s+(?:ft\.?|feat\.?|featuring)\s+", re.IGNORECASE)
_SPLIT_PATTERN = re.compile(r"\s*,\s*")


def _parse(artist_str: str) -> tuple[str, list[str]]:
    parts = _FEAT_PATTERN.split(artist_str, maxsplit=1)
    primary = parts[0].strip()
    featured = (
        [a.strip() for a in _SPLIT_PATTERN.split(parts[1]) if a.strip()]
        if len(parts) > 1
        else []
    )
    return primary, featured


def upgrade() -> None:
    # 1. Create song_artists table
    op.create_table(
        "song_artists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("song_id", sa.String(), nullable=False),
        sa.Column("artist_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="primary"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["artist_id"], ["artists.id"]),
        sa.UniqueConstraint("song_id", "artist_id"),
    )
    op.create_index("ix_song_artists_song_id", "song_artists", ["song_id"])
    op.create_index("ix_song_artists_artist_id", "song_artists", ["artist_id"])

    # 2. Add display_name to artists
    op.add_column("artists", sa.Column("display_name", sa.String(), nullable=True))

    # 3. Backfill: parse every song's artist string and populate song_artists + display_name
    conn = op.get_bind()

    # Cache artist name → id
    artist_cache: dict[str, int] = {}
    for row in conn.execute(sa.text("SELECT id, name FROM artists")):
        artist_cache[row[1]] = row[0]

    def get_or_create_artist(name: str) -> int:
        normalized = name.lower().strip()
        if normalized in artist_cache:
            return artist_cache[normalized]
        conn.execute(
            sa.text(
                "INSERT INTO artists (name, display_name, image_status, bio_status) "
                "VALUES (:name, :display_name, 'not_checked', 'not_checked')"
            ),
            {"name": normalized, "display_name": name},
        )
        row = conn.execute(
            sa.text("SELECT id FROM artists WHERE name = :name"),
            {"name": normalized},
        ).fetchone()
        artist_cache[normalized] = row[0]
        return row[0]

    # Update display_name for existing artists (use original casing from songs)
    songs = conn.execute(sa.text("SELECT id, artist FROM songs")).fetchall()
    for song_id, artist_str in songs:
        if not artist_str:
            continue
        primary_name, featured_names = _parse(artist_str)

        primary_id = get_or_create_artist(primary_name)

        # Update song.artist_id FK shortcut
        conn.execute(
            sa.text("UPDATE songs SET artist_id = :aid WHERE id = :sid"),
            {"aid": primary_id, "sid": song_id},
        )

        # Insert primary link
        conn.execute(
            sa.text(
                "INSERT INTO song_artists (song_id, artist_id, role, display_order) "
                "VALUES (:sid, :aid, 'primary', 0) "
                "ON CONFLICT (song_id, artist_id) DO NOTHING"
            ),
            {"sid": song_id, "aid": primary_id},
        )

        # Insert featured links
        for i, feat_name in enumerate(featured_names, start=1):
            feat_id = get_or_create_artist(feat_name)
            conn.execute(
                sa.text(
                    "INSERT INTO song_artists (song_id, artist_id, role, display_order) "
                    "VALUES (:sid, :aid, 'featured', :ord) "
                    "ON CONFLICT (song_id, artist_id) DO NOTHING"
                ),
                {"sid": song_id, "aid": feat_id, "ord": i},
            )

    # Update display_name for all artists that don't have one yet
    conn.execute(
        sa.text(
            "UPDATE artists SET display_name = name WHERE display_name IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_song_artists_artist_id", table_name="song_artists")
    op.drop_index("ix_song_artists_song_id", table_name="song_artists")
    op.drop_table("song_artists")
    op.drop_column("artists", "display_name")
