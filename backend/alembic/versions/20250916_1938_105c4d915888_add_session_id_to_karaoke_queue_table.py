"""Add session_id to karaoke_queue table

Revision ID: 105c4d915888
Revises: 03f0374a4ae4
Create Date: 2025-09-16 19:38:49.634315

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '105c4d915888'
down_revision: Union[str, None] = '03f0374a4ae4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add session_id column to karaoke_queue table
    op.add_column('karaoke_queue', sa.Column('session_id', sa.String(), nullable=True))
    
    # Create foreign key constraint
    op.create_foreign_key(
        'karaoke_queue_session_id_fkey',
        'karaoke_queue', 'karaoke_sessions',
        ['session_id'], ['session_id']
    )
    
    # For existing records, we need to assign them to a default session
    # Since this is a migration, we'll create a default session for existing queue items
    # In a real scenario, you might want to handle this differently
    op.execute("""
        INSERT INTO karaoke_sessions (session_id, display_code, host_device_id, created_at, expires_at, is_active)
        VALUES ('default_session', '0000', 'migration_host', NOW(), NOW() + INTERVAL '24 hours', true)
        ON CONFLICT (session_id) DO NOTHING
    """)
    
    # Update existing queue items to use the default session
    op.execute("""
        UPDATE karaoke_queue SET session_id = 'default_session' WHERE session_id IS NULL
    """)
    
    # Make session_id not nullable
    op.alter_column('karaoke_queue', 'session_id', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove foreign key constraint
    op.drop_constraint('karaoke_queue_session_id_fkey', 'karaoke_queue', type_='foreignkey')
    
    # Remove session_id column
    op.drop_column('karaoke_queue', 'session_id')
