"""add primary_genre and genres fields

Revision ID: b2c3d4e5f6a7
Revises: f0a1b2c3d4e5
Create Date: 2026-03-23 17:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "f0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("songs", "genre", new_column_name="primary_genre")
    op.add_column(
        "songs",
        sa.Column(
            "genres",
            ARRAY(sa.String()),
            nullable=True,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("songs", "genres")
    op.alter_column("songs", "primary_genre", new_column_name="genre")
