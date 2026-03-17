"""add_performance_history_table

Revision ID: a1f2e3d4c5b6
Revises: f56ea70a4499
Create Date: 2026-03-16 18:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1f2e3d4c5b6"
down_revision: Union[str, None] = "f56ea70a4499"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "performance_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("song_id", sa.String(), nullable=True),
        sa.Column("singer_name", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(length=4), nullable=True),
        sa.Column(
            "performed_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["karaoke_sessions.session_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["song_id"],
            ["songs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_performance_history_performed_at",
        "performance_history",
        ["performed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_performance_history_performed_at", table_name="performance_history")
    op.drop_table("performance_history")
