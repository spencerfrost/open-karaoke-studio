"""rename_release_title_to_album

Revision ID: 05b03e51ddf0
Revises: 6e002eaf6490
Create Date: 2025-06-08 13:36:21.244514

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '05b03e51ddf0'
down_revision: Union[str, None] = '6e002eaf6490'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - rename release_title column to album for better UX."""
    # Rename release_title to album in songs table
    op.alter_column('songs', 'release_title', new_column_name='album')


def downgrade() -> None:
    """Downgrade schema - revert album back to release_title."""
    # Revert album back to release_title
    op.alter_column('songs', 'album', new_column_name='release_title')
