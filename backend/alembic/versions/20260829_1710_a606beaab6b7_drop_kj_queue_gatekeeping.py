"""drop kj queue gatekeeping

Removes the karaoke-jockey controls: the three host_settings columns that gated
queue submissions (queue_open, max_songs_per_singer, queue_submission_mode) and
the karaoke_queue.status column that carried the "pending" approval state.

host_settings itself survives as the per-host defaults table, holding
session_duration_hours.

Revision ID: a606beaab6b7
Revises: 20260826_1200_song_error_message
Create Date: 2026-08-29 17:10:27.830565

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a606beaab6b7"
down_revision: Union[str, None] = "20260826_1200_song_error_message"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("host_settings", "queue_submission_mode")
    op.drop_column("host_settings", "max_songs_per_singer")
    op.drop_column("host_settings", "queue_open")
    op.drop_column("karaoke_queue", "status")


def downgrade() -> None:
    # All four columns are NOT NULL, so restoring them needs server defaults to
    # backfill existing rows. These mirror f56ea70a4499, which created them.
    op.add_column(
        "karaoke_queue",
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
    )
    op.add_column(
        "host_settings",
        sa.Column("queue_open", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "host_settings",
        sa.Column(
            "max_songs_per_singer", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "host_settings",
        sa.Column(
            "queue_submission_mode",
            sa.String(),
            nullable=False,
            server_default="instant",
        ),
    )
