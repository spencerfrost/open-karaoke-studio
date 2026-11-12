"""artist credits

Artists get their MusicBrainz and YouTube Music ids and a table of other names
they go by. Each credit keeps the name printed on that recording. Batch runs get
a report column, which the artist credits rebuild fills.

No data changes: the rebuild job on the admin Jobs page does those.

Revision ID: d4b8e1f6a273
Revises: a3c9e7d1f205
Create Date: 2026-10-25 22:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4b8e1f6a273"
down_revision: Union[str, None] = "a3c9e7d1f205"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("artists") as batch:
        batch.add_column(sa.Column("musicbrainz_artist_id", sa.String(), nullable=True))
        batch.add_column(
            sa.Column("youtube_music_artist_id", sa.String(), nullable=True)
        )
        batch.create_unique_constraint(
            "uq_artists_musicbrainz_artist_id", ["musicbrainz_artist_id"]
        )
        batch.create_unique_constraint(
            "uq_artists_youtube_music_artist_id", ["youtube_music_artist_id"]
        )

    op.add_column("song_artists", sa.Column("credited_as", sa.String(), nullable=True))

    op.create_table(
        "artist_aliases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "artist_id",
            sa.Integer(),
            sa.ForeignKey("artists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
    )
    op.create_index("ix_artist_aliases_artist_id", "artist_aliases", ["artist_id"])

    op.add_column("batch_runs", sa.Column("report", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("batch_runs", "report")
    op.drop_index("ix_artist_aliases_artist_id", table_name="artist_aliases")
    op.drop_table("artist_aliases")
    op.drop_column("song_artists", "credited_as")
    with op.batch_alter_table("artists") as batch:
        batch.drop_constraint("uq_artists_youtube_music_artist_id", type_="unique")
        batch.drop_constraint("uq_artists_musicbrainz_artist_id", type_="unique")
        batch.drop_column("youtube_music_artist_id")
        batch.drop_column("musicbrainz_artist_id")
