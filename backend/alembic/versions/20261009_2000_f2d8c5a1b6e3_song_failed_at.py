"""song failed_at

When a song last failed, for the admin failed songs list.

Songs that already failed take the finish time of their last failed job,
where one is still kept. Those times were written in the server's local
time, which is UTC in the Docker images.

Revision ID: f2d8c5a1b6e3
Revises: e1c7b4a9f352
Create Date: 2026-10-09 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2d8c5a1b6e3'
down_revision: Union[str, None] = 'e1c7b4a9f352'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('songs', sa.Column('failed_at', sa.DateTime(), nullable=True))
    op.execute(
        """
        UPDATE songs SET failed_at = (
            SELECT MAX(jobs.completed_at) FROM jobs
            WHERE jobs.song_id = songs.id AND jobs.status = 'failed'
        )
        WHERE songs.status = 'error'
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('songs', 'failed_at')
