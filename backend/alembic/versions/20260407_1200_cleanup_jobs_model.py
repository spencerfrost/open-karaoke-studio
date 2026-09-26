"""Cleanup jobs model — remove dead fields and stale records

Revision ID: 20260407_1200_cleanup_jobs
Revises: 20260331_1800_collapse_lyrics
Create Date: 2026-04-07 12:00:00.000000

Removes dead weight from the jobs table:
- Bulk-deletes all completed/failed/cancelled job records (1,728 stale rows)
- Drops dismissed, notes, phase, phase_message, retry_count columns

Jobs are now transient processing records deleted automatically upon completion.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260407_1200_cleanup_jobs"
down_revision = "20260331_1800_collapse_lyrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Delete all terminal-state job records — they pile up forever since
    # the `dismissed` mechanism was abandoned. Jobs are now auto-deleted
    # by the Celery tasks upon reaching a terminal state.
    op.execute(
        "DELETE FROM jobs WHERE status IN ('completed', 'failed', 'cancelled')"
    )

    op.drop_column("jobs", "dismissed")
    op.drop_column("jobs", "notes")
    op.drop_column("jobs", "phase")
    op.drop_column("jobs", "phase_message")
    op.drop_column("jobs", "retry_count")


def downgrade() -> None:
    op.add_column("jobs", sa.Column("retry_count", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("phase_message", sa.Text(), nullable=True))
    op.add_column(
        "jobs",
        sa.Column("phase", sa.String(), nullable=True, server_default="created"),
    )
    op.add_column("jobs", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column(
        "jobs",
        sa.Column("dismissed", sa.Boolean(), nullable=True, server_default="false"),
    )
