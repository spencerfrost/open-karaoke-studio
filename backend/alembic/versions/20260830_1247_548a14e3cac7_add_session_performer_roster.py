"""add session performer roster

Adds `session_performers`, the name-bound roster table for unit 3a (see
docs/plans/archive/2026-08-29-roster-and-rotation.md). Links `karaoke_queue` and
`performance_history` to it via a nullable `performer_id`, backfilled by
normalized name from the existing `singer_name` columns - `singer_name`
itself is kept as the display fallback. Also adds `karaoke_queue.created_at`,
which never existed even though both queue serializers have always guarded
for it and `addedAt` has been null in every payload the app has ever sent.

Revision ID: 548a14e3cac7
Revises: a606beaab6b7
Create Date: 2026-08-30 12:47:09.747346

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "548a14e3cac7"
down_revision: Union[str, None] = "a606beaab6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_performers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.String(length=4),
            sa.ForeignKey("karaoke_sessions.session_id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("normalized_name", sa.String(length=100), nullable=False),
        sa.Column("seat", sa.Integer(), nullable=False),
        sa.Column("laps_taken", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.UniqueConstraint(
            "session_id", "normalized_name", name="uq_session_performer_name"
        ),
    )

    op.add_column(
        "karaoke_queue",
        sa.Column(
            "performer_id",
            sa.Integer(),
            sa.ForeignKey("session_performers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "karaoke_queue",
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
    )

    op.add_column(
        "performance_history",
        sa.Column(
            "performer_id",
            sa.Integer(),
            sa.ForeignKey("session_performers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "performance_history",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Backfill: one roster row per distinct (session_id, normalized name) pair
    # seen across the queue and performance history. Both tables' session_id
    # columns are FK-constrained when non-null, so every session_id here
    # already references a live karaoke_sessions row.
    op.execute("""
        WITH names AS (
            SELECT session_id, singer_name AS name FROM karaoke_queue
            UNION ALL
            SELECT session_id, singer_name AS name FROM performance_history
            WHERE session_id IS NOT NULL
        ),
        normalized AS (
            SELECT session_id, name, lower(trim(name)) AS normalized_name
            FROM names
            WHERE trim(name) <> ''
        ),
        representative AS (
            SELECT DISTINCT ON (session_id, normalized_name)
                session_id, normalized_name, name
            FROM normalized
            ORDER BY session_id, normalized_name, name
        ),
        seated AS (
            SELECT session_id, name, normalized_name,
                   row_number() OVER (PARTITION BY session_id ORDER BY normalized_name) - 1 AS seat
            FROM representative
        )
        INSERT INTO session_performers
            (session_id, name, normalized_name, seat, laps_taken, is_active, created_at)
        SELECT session_id, name, normalized_name, seat, 0, true, now()
        FROM seated
        """)

    op.execute("""
        UPDATE karaoke_queue kq
        SET performer_id = sp.id
        FROM session_performers sp
        WHERE kq.session_id = sp.session_id
          AND lower(trim(kq.singer_name)) = sp.normalized_name
        """)

    op.execute("""
        UPDATE performance_history ph
        SET performer_id = sp.id
        FROM session_performers sp
        WHERE ph.session_id IS NOT NULL
          AND ph.session_id = sp.session_id
          AND lower(trim(ph.singer_name)) = sp.normalized_name
        """)


def downgrade() -> None:
    op.drop_column("performance_history", "user_id")
    op.drop_column("performance_history", "performer_id")
    op.drop_column("karaoke_queue", "created_at")
    op.drop_column("karaoke_queue", "performer_id")
    op.drop_table("session_performers")
