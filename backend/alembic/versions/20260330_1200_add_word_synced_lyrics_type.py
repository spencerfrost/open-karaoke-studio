"""Add word_synced lyrics type

Revision ID: 20260330_1200_word_synced
Revises: 2a3b4c5d6e7f
Create Date: 2026-03-30 12:00:00.000000

Widens the lyrics.type column from VARCHAR(10) to VARCHAR(20) to accommodate
the new 'word_synced' type alongside existing 'plain' and 'synced' types.

Also drops and recreates the CHECK constraint to include 'word_synced'.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260330_1200_word_synced"
down_revision = "2a3b4c5d6e7f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Widen the type column to fit 'word_synced' (11 chars)
    op.alter_column(
        "lyrics",
        "type",
        existing_type=sa.String(10),
        type_=sa.String(20),
        existing_nullable=False,
    )

    # Drop existing check constraint if present (ignore if it doesn't exist)
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid = 'lyrics'::regclass AND contype = 'c' AND conname = 'lyrics_type_check'"
        )
    ).fetchone()
    if result:
        op.drop_constraint("lyrics_type_check", "lyrics", type_="check")

    op.create_check_constraint(
        "lyrics_type_check",
        "lyrics",
        "type IN ('plain', 'synced', 'word_synced')",
    )


def downgrade() -> None:
    # Remove the updated constraint
    op.drop_constraint("lyrics_type_check", "lyrics", type_="check")

    # Restore old constraint (no word_synced)
    op.create_check_constraint(
        "lyrics_type_check",
        "lyrics",
        "type IN ('plain', 'synced')",
    )

    # Narrow column back — will fail if any word_synced rows exist
    op.alter_column(
        "lyrics",
        "type",
        existing_type=sa.String(20),
        type_=sa.String(10),
        existing_nullable=False,
    )
