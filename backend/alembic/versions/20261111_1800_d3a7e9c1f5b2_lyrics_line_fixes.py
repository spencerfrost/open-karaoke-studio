"""lyrics_line_fixes

A person fixing one line of lyrics on the stage. Each fix is a row, kept over
whatever the song's lyrics are later: every job that stores lyrics puts the
fixed text back on its line.

Revision ID: d3a7e9c1f5b2
Revises: c8d2f5a1e9b4
Create Date: 2026-11-11 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d3a7e9c1f5b2"
down_revision: Union[str, None] = "c8d2f5a1e9b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "lyrics_line_fixes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "song_id",
            sa.String(),
            sa.ForeignKey("songs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("old_text", sa.Text(), nullable=False),
        sa.Column("new_text", sa.Text(), nullable=False),
        sa.Column("line_start", sa.Float(), nullable=True),
        sa.Column("prev_text", sa.Text(), nullable=True),
        sa.Column("next_text", sa.Text(), nullable=True),
        sa.Column("occurrence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("words_key", sa.String(), nullable=True),
        sa.Column("word_timing_aligned_at", sa.String(), nullable=True),
        sa.Column(
            "align_status", sa.String(), nullable=False, server_default="pending"
        ),
        sa.Column("aligned_at", sa.DateTime(), nullable=True),
        sa.Column("fixed_by", sa.String(), nullable=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_lyrics_line_fixes_song_id", "lyrics_line_fixes", ["song_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_lyrics_line_fixes_song_id", table_name="lyrics_line_fixes")
    op.drop_table("lyrics_line_fixes")
