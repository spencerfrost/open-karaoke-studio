"""readd_bpm_for_count_in

Revision ID: 618143a6fa78
Revises: d335baa6b48b
Create Date: 2026-01-03 13:41:01.454616

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '618143a6fa78'
down_revision: Union[str, None] = 'd335baa6b48b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('songs', sa.Column('bpm', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('songs', 'bpm')
