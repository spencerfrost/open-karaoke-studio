"""song_step_versions

Which version of each processing step produced a song's data (see
app.services.processing_versions). Loudness, singing maps and vocal ranges
already stored were made by version 1. Word timing starts empty everywhere:
existing timings predate aligning on the lead + backing mix.

Revision ID: f4a8c2e6b1d3
Revises: e3c7b1d9f2a6
Create Date: 2026-11-10 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f4a8c2e6b1d3"
down_revision: Union[str, None] = "e3c7b1d9f2a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# New column, and the column that says the step has already run.
STAMPED_FROM = {
    "loudness_version": "loudness_lufs",
    "singing_map_version": "singing_map",
    "vocal_range_version": "vocal_range_low",
}


def upgrade() -> None:
    """Upgrade schema."""
    for column in (*STAMPED_FROM, "word_timing_version"):
        op.add_column("songs", sa.Column(column, sa.Integer(), nullable=True))
    for column, data_column in STAMPED_FROM.items():
        op.execute(f"UPDATE songs SET {column} = 1 WHERE {data_column} IS NOT NULL")


def downgrade() -> None:
    """Downgrade schema."""
    for column in ("word_timing_version", *reversed(STAMPED_FROM)):
        op.drop_column("songs", column)
