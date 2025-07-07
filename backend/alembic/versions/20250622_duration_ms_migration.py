"""
Alembic migration: migrate song duration from float seconds (duration) to integer milliseconds (duration_ms).
- Adds duration_ms column (Integer, nullable)
- Backfills duration_ms = duration * 1000
- Drops duration column (if possible)
- SQLite: duration column will remain unless you do a table-copy workaround
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250622_duration_ms_migration"
down_revision = "addbfd875d80"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add duration_ms column, nullable
    op.add_column("songs", sa.Column("duration_ms", sa.Integer(), nullable=True))

    # 2. Backfill duration_ms from duration
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE songs SET duration_ms = CAST(ROUND(duration * 1000) AS INTEGER) WHERE duration IS NOT NULL"
        )
    )

    # 3. Drop duration column (SQLite can't drop columns, so this is a no-op for SQLite)
    # For other DBs, you could:
    # op.drop_column("songs", "duration")


def downgrade():
    # Not implemented: would require similar logic in reverse
    raise NotImplementedError("Downgrade not supported for this migration.")
