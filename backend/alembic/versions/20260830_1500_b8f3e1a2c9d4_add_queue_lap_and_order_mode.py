"""add queue lap and order mode

Adds unit 3b's rotation mechanism (see docs/plans/2026-08-29-roster-and-rotation.md,
Stage 3b): `karaoke_queue.lap`, computed once at insert and never recomputed, plus
`karaoke_sessions.queue_order_mode` ("append" | "rotation", default rotation) and
`karaoke_sessions.current_lap`, the lap playback has reached.

Existing queue rows predate the mechanism, so `lap` is backfilled the way
compute_lap would have assigned it: each performer's Nth song in a session is
their Nth turn, i.e. lap N-1. Without this every existing row sits at lap 0 and
the sort collapses to seat order, clumping each singer's songs together. Where
a session has a song loaded, `current_lap` and that singer's `laps_taken` are
seeded from it so the rotation resumes where the room actually is.

Revision ID: b8f3e1a2c9d4
Revises: 548a14e3cac7
Create Date: 2026-08-30 15:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8f3e1a2c9d4"
down_revision: Union[str, None] = "548a14e3cac7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "karaoke_queue",
        sa.Column("lap", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "karaoke_sessions",
        sa.Column(
            "queue_order_mode",
            sa.String(length=20),
            nullable=False,
            server_default="rotation",
        ),
    )
    op.add_column(
        "karaoke_sessions",
        sa.Column("current_lap", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "session_performers",
        sa.Column("first_queued_at", sa.DateTime(), nullable=True),
    )

    # Entering the rotation is queueing, not joining, so backfill from the
    # earliest song each performer put in - the queue first, then history for
    # anyone whose queued songs have all been sung already.
    op.execute("""
        UPDATE session_performers sp
        SET first_queued_at = earliest.first_queued_at
        FROM (
            SELECT performer_id, min(created_at) AS first_queued_at
            FROM karaoke_queue
            WHERE performer_id IS NOT NULL
            GROUP BY performer_id
        ) earliest
        WHERE sp.id = earliest.performer_id
        """)

    op.execute("""
        UPDATE session_performers sp
        SET first_queued_at = earliest.first_performed_at
        FROM (
            SELECT performer_id, min(performed_at) AS first_performed_at
            FROM performance_history
            WHERE performer_id IS NOT NULL
            GROUP BY performer_id
        ) earliest
        WHERE sp.id = earliest.performer_id
          AND (
              sp.first_queued_at IS NULL
              OR earliest.first_performed_at < sp.first_queued_at
          )
        """)

    # Each performer's Nth song in a session is their Nth turn, so it belongs on
    # lap N-1 - the same result compute_lap would have produced had the column
    # existed when these rows were inserted.
    op.execute("""
        UPDATE karaoke_queue kq
        SET lap = numbered.turn
        FROM (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY session_id, performer_id ORDER BY id
                   ) - 1 AS turn
            FROM karaoke_queue
        ) numbered
        WHERE kq.id = numbered.id
        """)

    # A session with a song loaded has already reached that song's lap, and its
    # singer has spent that turn - seed both so the rotation resumes correctly.
    op.execute("""
        UPDATE karaoke_sessions ks
        SET current_lap = kq.lap
        FROM session_playback_states sps
        JOIN karaoke_queue kq ON kq.id = sps.current_queue_item_id
        WHERE sps.session_id = ks.session_id
        """)

    op.execute("""
        UPDATE session_performers sp
        SET laps_taken = kq.lap + 1
        FROM session_playback_states sps
        JOIN karaoke_queue kq ON kq.id = sps.current_queue_item_id
        WHERE kq.performer_id = sp.id
        """)


def downgrade() -> None:
    op.drop_column("session_performers", "first_queued_at")
    op.drop_column("karaoke_sessions", "current_lap")
    op.drop_column("karaoke_sessions", "queue_order_mode")
    op.drop_column("karaoke_queue", "lap")
