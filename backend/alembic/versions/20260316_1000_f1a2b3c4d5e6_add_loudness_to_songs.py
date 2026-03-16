"""add loudness to songs

Revision ID: f1a2b3c4d5e6
Revises: e8f9a0b1c2d3
Create Date: 2026-03-16 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("songs", sa.Column("loudness_dbfs", sa.Float(), nullable=True))
    op.add_column("songs", sa.Column("gain_db", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("songs", "gain_db")
    op.drop_column("songs", "loudness_dbfs")
