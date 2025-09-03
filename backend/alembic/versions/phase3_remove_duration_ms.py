"""
Phase 3: Remove duration_ms column after migration to seconds

Revision ID: phase3_remove_duration_ms
Revises: 20250903_migrate_back_to_seconds
Create Date: 2025-09-03 15:00:00.000000

This migration removes the legacy duration_ms column after successful migration to seconds.
Only run this after confirming:
1. All frontend applications are updated to use the new duration field (seconds)
2. All API consumers have been migrated
3. Tests are passing with the new field
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "phase3_remove_duration_ms"
down_revision = "20250903_migrate_back_to_seconds"
branch_labels = None
depends_on = None


def upgrade():
    """
    Phase 3: Remove duration_ms column
    
    This is a destructive operation - the duration_ms column will be permanently deleted.
    Ensure all applications are using the new duration field (seconds) before running.
    """
    # Drop the legacy duration_ms column
    op.drop_column('songs', 'duration_ms')
    print("Successfully removed duration_ms column from songs table")


def downgrade():
    """
    Restore duration_ms column and populate from duration
    
    This restores the legacy column in case rollback is needed.
    """
    # Re-add the duration_ms column
    op.add_column('songs', sa.Column('duration_ms', sa.Integer(), nullable=True))
    
    # Populate duration_ms from duration (convert seconds to milliseconds)
    op.execute("""
        UPDATE songs 
        SET duration_ms = CAST(duration * 1000 AS INTEGER) 
        WHERE duration IS NOT NULL
    """)
    
    print("Restored duration_ms column and populated from duration field")