"""add error_message to songs

Revision ID: 20260826_1200_song_error_message
Revises: 20260711_1200_show_name
Create Date: 2026-08-26 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260826_1200_song_error_message"
down_revision: Union[str, None] = "20260711_1200_show_name"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("songs", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("songs", "error_message")
