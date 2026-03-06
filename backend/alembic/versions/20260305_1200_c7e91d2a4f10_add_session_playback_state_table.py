"""add_session_playback_state_table

Add persistent session playback state table to separate current loaded song
from queue ordering.

Revision ID: c7e91d2a4f10
Revises: a1b2c3d4e5f6
Create Date: 2026-03-05 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7e91d2a4f10"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create session_playback_states table."""
    op.create_table(
        "session_playback_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=4), nullable=False),
        sa.Column("current_queue_item_id", sa.Integer(), nullable=True),
        sa.Column("current_song_id", sa.String(), nullable=True),
        sa.Column(
            "is_playing", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "current_time", sa.Float(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("duration", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "is_ready", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["karaoke_sessions.session_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["current_queue_item_id"], ["karaoke_queue.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["current_song_id"], ["songs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index(
        "ix_session_playback_states_session_id",
        "session_playback_states",
        ["session_id"],
        unique=True,
    )


def downgrade() -> None:
    """Drop session_playback_states table."""
    op.drop_index(
        "ix_session_playback_states_session_id", table_name="session_playback_states"
    )
    op.drop_table("session_playback_states")
