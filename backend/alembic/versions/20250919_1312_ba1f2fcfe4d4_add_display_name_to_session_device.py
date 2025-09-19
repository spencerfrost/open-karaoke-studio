"""add_display_name_to_session_device

Revision ID: ba1f2fcfe4d4
Revises: 105c4d915888
Create Date: 2025-09-19 13:12:31.849216

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ba1f2fcfe4d4'
down_revision: Union[str, None] = '105c4d915888'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add display_name column to session_devices table
    op.add_column('session_devices', sa.Column('display_name', sa.String(100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove display_name column from session_devices table
    op.drop_column('session_devices', 'display_name')
