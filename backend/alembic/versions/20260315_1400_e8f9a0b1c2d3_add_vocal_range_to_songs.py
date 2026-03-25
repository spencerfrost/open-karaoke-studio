"""add vocal range to songs

Revision ID: e8f9a0b1c2d3
Revises: c7e91d2a4f10
Create Date: 2026-03-15 14:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8f9a0b1c2d3"
down_revision: Union[str, None] = "c7e91d2a4f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("songs", sa.Column("vocal_range_low", sa.String(), nullable=True))
    op.add_column("songs", sa.Column("vocal_range_high", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("songs", "vocal_range_high")
    op.drop_column("songs", "vocal_range_low")
