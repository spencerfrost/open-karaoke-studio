"""Collapse lyrics table into song columns

Revision ID: 20260331_1800_collapse_lyrics
Revises: 20260330_1200_word_synced
Create Date: 2026-03-31 18:00:00.000000

Removes the lyrics versioning table and moves lyrics back to simple TEXT columns
on the songs table. Adds word_synced_lyrics to store alignment JSON.
"""

import json

import sqlalchemy as sa
from alembic import op

revision = "20260331_1800_collapse_lyrics"
down_revision = "20260330_1200_word_synced"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Add word_synced_lyrics column to songs
    op.add_column("songs", sa.Column("word_synced_lyrics", sa.Text(), nullable=True))

    # 2. Backfill plain_lyrics from active lyrics rows (overwrite legacy column values)
    conn.execute(sa.text("""
        UPDATE songs
        SET plain_lyrics = l.content
        FROM lyrics l
        WHERE l.song_id = songs.id
          AND l.type = 'plain'
          AND l.is_active = true
    """))

    # 3. Backfill synced_lyrics from active lyrics rows
    conn.execute(sa.text("""
        UPDATE songs
        SET synced_lyrics = l.content
        FROM lyrics l
        WHERE l.song_id = songs.id
          AND l.type = 'synced'
          AND l.is_active = true
    """))

    # 4. Backfill word_synced_lyrics — merge words array + metadata into one JSON object
    rows = conn.execute(sa.text("""
        SELECT song_id, content, metadata
        FROM lyrics
        WHERE type = 'word_synced' AND is_active = true
    """)).fetchall()

    for song_id, content, metadata in rows:
        try:
            words = json.loads(content) if isinstance(content, str) else content
            meta = metadata if isinstance(metadata, dict) else {}
            merged = {
                "words": words,
                "language": meta.get("language", "en"),
                "mean_score": meta.get("mean_score"),
                "word_count": meta.get("word_count"),
                "line_count": meta.get("line_count"),
                "aligned_at": meta.get("aligned_at"),
            }
            conn.execute(
                sa.text("UPDATE songs SET word_synced_lyrics = :val WHERE id = :sid"),
                {"val": json.dumps(merged), "sid": song_id},
            )
        except Exception:
            pass  # leave NULL if data is malformed

    # 5. Drop lyrics table
    op.drop_table("lyrics")


def downgrade() -> None:
    # Recreate the lyrics table (schema only — data is not recoverable)
    op.create_table(
        "lyrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("song_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("type IN ('plain', 'synced', 'word_synced')", name="lyrics_type_check"),
    )
    op.create_index("idx_lyrics_song_id", "lyrics", ["song_id"])
    op.create_index("idx_lyrics_song_type_active", "lyrics", ["song_id", "type", "is_active"])

    op.drop_column("songs", "word_synced_lyrics")
