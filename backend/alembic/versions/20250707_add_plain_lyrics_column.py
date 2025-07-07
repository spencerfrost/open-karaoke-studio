"""
Add plain_lyrics column to songs table (deprecate lyrics)

Revision ID: 20250707_add_plain_lyrics_column
Revises: d048757b81a8
Create Date: 2025-07-07
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250707_add_plain_lyrics_column"
down_revision = "d048757b81a8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("songs", sa.Column("plain_lyrics", sa.Text(), nullable=True))
    # Optionally, copy data from lyrics to plain_lyrics
    op.execute("UPDATE songs SET plain_lyrics = lyrics WHERE lyrics IS NOT NULL")
    # (Do not drop lyrics column yet for safe migration)


def downgrade():
    op.drop_column("songs", "plain_lyrics")
