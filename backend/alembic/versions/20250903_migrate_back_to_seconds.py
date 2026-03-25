# pylint: skip-file
"""
Alembic migration: migrate song duration from integer milliseconds (duration_ms) back to float seconds (duration).
- Adds duration column (Float, nullable)
- Backfills duration = duration_ms / 1000.0
- Keeps duration_ms temporarily for backwards compatibility
- During transition phase, both columns exist
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250903_migrate_back_to_seconds"
down_revision = "601713691424"  # Points to initial_postgres_schema
branch_labels = None
depends_on = None


def upgrade():
    """
    Phase 1: Add duration column and populate from duration_ms
    """
    # Add the new duration column (Float for seconds)
    op.add_column('songs', sa.Column('duration', sa.Float(), nullable=True))
    
    # Populate duration from duration_ms (convert milliseconds to seconds)
    op.execute("""
        UPDATE songs 
        SET duration = CAST(duration_ms AS FLOAT) / 1000.0 
        WHERE duration_ms IS NOT NULL
    """)


def downgrade():
    """
    Reverse the migration by dropping the duration column
    """
    op.drop_column('songs', 'duration')