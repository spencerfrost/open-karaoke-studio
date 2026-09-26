"""drop_performer_consecutive_passes

The handoff screen no longer auto-passes an empty seat, and a seat is no longer
deactivated after two passes nobody stepped up for. This is a living-room app:
nobody is rushed, and a roster only shrinks when someone taps "Skip me for now"
or the host removes them. The counter existed only to drive that removal.

Revision ID: e2a6c8d4f913
Revises: b7d4f2e91a3c
Create Date: 2026-09-23 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2a6c8d4f913'
down_revision: Union[str, None] = 'b7d4f2e91a3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('session_performers', 'consecutive_passes')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        'session_performers',
        sa.Column(
            'consecutive_passes', sa.Integer(), nullable=False, server_default='0'
        ),
    )
