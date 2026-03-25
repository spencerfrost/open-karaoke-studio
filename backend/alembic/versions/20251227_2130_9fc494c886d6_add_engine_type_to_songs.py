"""Add engine_type to songs table

Revision ID: 9fc494c886d6
Revises: 234d85ef0e00
Create Date: 2025-12-27 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9fc494c886d6'
down_revision: Union[str, None] = '234d85ef0e00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add engine_type column to songs table."""
    op.add_column('songs', sa.Column('engine_type', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove engine_type column from songs table."""
    op.drop_column('songs', 'engine_type')
