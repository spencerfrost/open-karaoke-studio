"""acoustid suggestions

AcoustID stops renaming songs: a match that names a song differently is kept
as a suggestion, and a person's title/artist is marked confirmed so automatic
runs leave it alone.

Songs already marked "skipped" were fixed by hand, so they start confirmed.
Songs AcoustID couldn't settle (ambiguous, no_match, failed) lose the recording
an earlier run linked; it no longer describes them, and credits trust it.

Revision ID: b7c4e2d9a816
Revises: a3e9d6c2f147
Create Date: 2026-10-10 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b7c4e2d9a816"
down_revision: Union[str, None] = "a3e9d6c2f147"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "songs",
        sa.Column("acoustid_suggested_recording_id", sa.String(), nullable=True),
    )
    op.add_column(
        "songs", sa.Column("acoustid_suggested_title", sa.String(), nullable=True)
    )
    op.add_column(
        "songs", sa.Column("acoustid_suggested_artist", sa.String(), nullable=True)
    )
    op.add_column(
        "songs", sa.Column("metadata_confirmed_at", sa.DateTime(), nullable=True)
    )
    op.execute("""
        UPDATE songs SET metadata_confirmed_at = CURRENT_TIMESTAMP
        WHERE acoustid_fingerprint_status = 'skipped'
        """)
    op.execute("""
        UPDATE songs SET musicbrainz_recording_id = NULL
        WHERE acoustid_fingerprint_status IN ('ambiguous', 'no_match', 'failed')
        """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("songs", "metadata_confirmed_at")
    op.drop_column("songs", "acoustid_suggested_artist")
    op.drop_column("songs", "acoustid_suggested_title")
    op.drop_column("songs", "acoustid_suggested_recording_id")
