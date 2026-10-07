"""lyrics_report_snapshot

A report keeps the lyrics that were on screen when it was first made, so an
admin who decides the report was wrong can put those lyrics back.

Revision ID: c4f2a7e1b903
Revises: b7d41e9a2c58
Create Date: 2026-10-06 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4f2a7e1b903'
down_revision: Union[str, None] = 'b7d41e9a2c58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('lyrics_reports', sa.Column('reported_synced_lyrics', sa.Text(), nullable=True))
    op.add_column('lyrics_reports', sa.Column('reported_plain_lyrics', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('lyrics_reports', 'reported_plain_lyrics')
    op.drop_column('lyrics_reports', 'reported_synced_lyrics')
