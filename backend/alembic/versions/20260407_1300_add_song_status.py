"""Add status column to songs table

Revision ID: 20260407_1300_add_song_status
Revises: 20260407_1200_cleanup_jobs
Create Date: 2026-04-07 13:00:00.000000

Adds a status column to songs: processing | processed | error.
Existing rows are backfilled to 'processed' since they have audio files.
New songs start as 'processing' and are updated by Celery tasks on completion or failure.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260407_1300_add_song_status"
down_revision = "20260407_1200_cleanup_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "songs",
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="processing",
        ),
    )
    # Existing songs all have audio files — mark them as processed.
    op.execute("UPDATE songs SET status = 'processed'")


def downgrade() -> None:
    op.drop_column("songs", "status")
