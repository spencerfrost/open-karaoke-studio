"""add show_name to songs

Revision ID: 20260711_1200_show_name
Revises: 20260710_0900_demo_pool
Create Date: 2026-07-11 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260711_1200_show_name"
down_revision: Union[str, None] = "20260710_0900_demo_pool"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("songs", sa.Column("show_name", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("songs", "show_name")
