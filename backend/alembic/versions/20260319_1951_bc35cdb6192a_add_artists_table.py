"""add_artists_table

Revision ID: bc35cdb6192a
Revises: a1f2e3d4c5b6
Create Date: 2026-03-19 19:51:17.424296

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'bc35cdb6192a'
down_revision: Union[str, None] = 'a1f2e3d4c5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'artists',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('image_path', sa.String(), nullable=True),
        sa.Column('image_status', sa.String(), nullable=False, server_default='not_checked'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )


def downgrade() -> None:
    op.drop_table('artists')
