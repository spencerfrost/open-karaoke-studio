"""show name hand set

Songs gain show_name_hand_set_at: a person set or cleared the show name, so it
isn't taken from the song's MusicBrainz recording any more. Existing show
names stay unmarked; the artist credits rebuild sets them from the recording.

Revision ID: e7a2c9f4b318
Revises: d4b8e1f6a273
Create Date: 2026-10-26 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e7a2c9f4b318"
down_revision: Union[str, None] = "d4b8e1f6a273"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "songs", sa.Column("show_name_hand_set_at", sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("songs", "show_name_hand_set_at")
