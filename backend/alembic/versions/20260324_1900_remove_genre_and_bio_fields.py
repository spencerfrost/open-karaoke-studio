"""remove genre and bio fields

Revision ID: 2a3b4c5d6e7f
Revises: b2c3d4e5f6a7
Create Date: 2026-03-24 19:00:00.000000
"""
from alembic import op

revision = "2a3b4c5d6e7f"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("songs", "primary_genre")
    op.drop_column("songs", "genres")
    op.drop_column("artists", "bio")
    op.drop_column("artists", "bio_status")


def downgrade() -> None:
    import sqlalchemy as sa
    from sqlalchemy.dialects.postgresql import ARRAY

    op.add_column("artists", sa.Column("bio_status", sa.String(), nullable=False, server_default="not_checked"))
    op.add_column("artists", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column("songs", sa.Column("genres", ARRAY(sa.String()), nullable=True, server_default="{}"))
    op.add_column("songs", sa.Column("primary_genre", sa.String(), nullable=True))
