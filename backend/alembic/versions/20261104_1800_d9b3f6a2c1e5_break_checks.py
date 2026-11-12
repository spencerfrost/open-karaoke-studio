"""break_checks

Answers given by ear on the admin Compare breaks page: for each moment,
whether the singing map or today's word-gap bar was right.

Revision ID: d9b3f6a2c1e5
Revises: c4e8a2f17b93
Create Date: 2026-11-04 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d9b3f6a2c1e5"
down_revision: Union[str, None] = "c4e8a2f17b93"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "break_checks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "song_id",
            sa.String(),
            sa.ForeignKey("songs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("moment_key", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("answer", sa.String(), nullable=False),
        sa.Column("moment", sa.Text(), nullable=False),
        sa.Column("map_params", sa.Text(), nullable=True),
        sa.Column("map_measured_at", sa.String(), nullable=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "song_id", "moment_key", name="uq_break_checks_song_moment"
        ),
    )
    op.create_index("ix_break_checks_song_id", "break_checks", ["song_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_break_checks_song_id", table_name="break_checks")
    op.drop_table("break_checks")
