"""lyrics_feedback

After each song the stage asks "How were the lyrics?". Each answer is a row,
one per queue item, tied to the lyrics and word timings that were on screen.

Revision ID: f1c6d2a8e947
Revises: b3f7a1d9c625
Create Date: 2026-10-28 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f1c6d2a8e947"
down_revision: Union[str, None] = "b3f7a1d9c625"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "lyrics_feedback",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "song_id",
            sa.String(),
            sa.ForeignKey("songs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("queue_item_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.String(), nullable=False),
        sa.Column("words_key", sa.String(), nullable=False),
        sa.Column("word_timing_aligned_at", sa.String(), nullable=True),
        sa.Column("singer_name", sa.String(), nullable=True),
        sa.Column("answered_by", sa.String(), nullable=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "session_id",
            sa.String(length=4),
            sa.ForeignKey("karaoke_sessions.session_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("queue_item_id", name="uq_lyrics_feedback_queue_item"),
    )
    op.create_index("ix_lyrics_feedback_song_id", "lyrics_feedback", ["song_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_lyrics_feedback_song_id", table_name="lyrics_feedback")
    op.drop_table("lyrics_feedback")
