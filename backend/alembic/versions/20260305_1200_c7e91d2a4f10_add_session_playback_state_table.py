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

    bind = op.get_bind()

    legacy_current_rows = bind.execute(sa.text("""
            SELECT
                q.session_id,
                q.id AS queue_item_id,
                q.song_id,
                COALESCE(s.duration, 0) AS duration
            FROM karaoke_queue q
            LEFT JOIN songs s ON s.id = q.song_id
            WHERE q.position = 0
            ORDER BY q.id
            """)).fetchall()

    for row in legacy_current_rows:
        existing_state = bind.execute(
            sa.text(
                "SELECT id, current_queue_item_id FROM session_playback_states WHERE session_id = :session_id"
            ),
            {"session_id": row.session_id},
        ).first()

        if existing_state is None:
            bind.execute(
                sa.text("""
                    INSERT INTO session_playback_states (
                        session_id,
                        current_queue_item_id,
                        current_song_id,
                        is_playing,
                        current_time,
                        duration,
                        is_ready
                    ) VALUES (
                        :session_id,
                        :queue_item_id,
                        :song_id,
                        false,
                        0,
                        :duration,
                        false
                    )
                    """),
                {
                    "session_id": row.session_id,
                    "queue_item_id": row.queue_item_id,
                    "song_id": row.song_id,
                    "duration": row.duration,
                },
            )
            continue

        if existing_state.current_queue_item_id is None:
            bind.execute(
                sa.text("""
                    UPDATE session_playback_states
                    SET
                        current_queue_item_id = :queue_item_id,
                        current_song_id = :song_id,
                        duration = CASE WHEN duration = 0 THEN :duration ELSE duration END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = :session_id
                    """),
                {
                    "session_id": row.session_id,
                    "queue_item_id": row.queue_item_id,
                    "song_id": row.song_id,
                    "duration": row.duration,
                },
            )

    playback_states = bind.execute(
        sa.text(
            "SELECT session_id, current_queue_item_id FROM session_playback_states ORDER BY session_id"
        )
    ).fetchall()

    for playback_state in playback_states:
        upcoming_rows = bind.execute(
            sa.text("""
                SELECT id
                FROM karaoke_queue
                WHERE session_id = :session_id
                  AND (:current_id IS NULL OR id != :current_id)
                ORDER BY position, id
                """),
            {
                "session_id": playback_state.session_id,
                "current_id": playback_state.current_queue_item_id,
            },
        ).fetchall()

        for idx, queue_row in enumerate(upcoming_rows, start=1):
            bind.execute(
                sa.text(
                    "UPDATE karaoke_queue SET position = :position WHERE id = :queue_item_id"
                ),
                {
                    "position": idx,
                    "queue_item_id": queue_row.id,
                },
            )


def downgrade() -> None:
    """Drop session_playback_states table."""
    op.drop_index(
        "ix_session_playback_states_session_id", table_name="session_playback_states"
    )
    op.drop_table("session_playback_states")
