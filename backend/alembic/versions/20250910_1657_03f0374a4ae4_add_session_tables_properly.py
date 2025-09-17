"""Add session tables properly

Revision ID: 03f0374a4ae4
Revises: e7ff805adf6d
Create Date: 2025-09-10 16:57:59.648185

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '03f0374a4ae4'
down_revision: Union[str, None] = 'e7ff805adf6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create karaoke_sessions table
    op.create_table('karaoke_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(length=32), nullable=False),
        sa.Column('display_code', sa.String(length=4), nullable=False),
        sa.Column('host_device_id', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('display_code'),
        sa.UniqueConstraint('session_id')
    )
    
    # Create session_devices table
    op.create_table('session_devices',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(length=32), nullable=False),
        sa.Column('device_id', sa.String(length=64), nullable=False),
        sa.Column('device_type', sa.String(length=20), nullable=False),
        sa.Column('joined_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['karaoke_sessions.session_id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('session_devices')
    op.drop_table('karaoke_sessions')
