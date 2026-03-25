"""Add engine_type to jobs table

Revision ID: 6dd07e747f45
Revises: ff709dcf3edf
Create Date: 2025-12-21 16:27:37.347564

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6dd07e747f45'
down_revision: Union[str, None] = 'ff709dcf3edf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add engine_type column to jobs table
    op.add_column('jobs', sa.Column('engine_type', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove engine_type column from jobs table
    op.drop_column('jobs', 'engine_type')
