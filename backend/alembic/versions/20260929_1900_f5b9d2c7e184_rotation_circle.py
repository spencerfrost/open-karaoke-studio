"""rotation_circle

Rotation becomes a fixed circle of seats with a pointer to whose turn it is,
replacing the per-item lap number and the three counters that held it
together.

`seat` and `is_active` keep their columns and values but change meaning: seat
is now the place in the circle, and is_active is "part of the night".

The downgrade re-adds the lap columns with their old defaults. Lap values
cannot be reconstructed, and the lap model rebuilds them from new inserts.

Revision ID: f5b9d2c7e184
Revises: e2a6c8d4f913
Create Date: 2026-09-29 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5b9d2c7e184'
down_revision: Union[str, None] = 'e2a6c8d4f913'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'karaoke_sessions',
        sa.Column('turn_performer_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_karaoke_sessions_turn_performer_id',
        'karaoke_sessions',
        'session_performers',
        ['turn_performer_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.add_column(
        'karaoke_sessions',
        sa.Column('bumped_item_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_karaoke_sessions_bumped_item_id',
        'karaoke_sessions',
        'karaoke_queue',
        ['bumped_item_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.add_column(
        'session_performers',
        sa.Column(
            'turns_borrowed', sa.Integer(), nullable=False, server_default='0'
        ),
    )

    op.drop_column('karaoke_queue', 'lap')
    op.drop_column('karaoke_sessions', 'current_lap')
    op.drop_column('session_performers', 'laps_taken')
    op.drop_column('session_performers', 'first_queued_at')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        'session_performers',
        sa.Column('first_queued_at', sa.DateTime(), nullable=True),
    )
    op.add_column(
        'session_performers',
        sa.Column('laps_taken', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'karaoke_sessions',
        sa.Column('current_lap', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'karaoke_queue',
        sa.Column('lap', sa.Integer(), nullable=False, server_default='0'),
    )

    op.drop_column('session_performers', 'turns_borrowed')
    op.drop_constraint(
        'fk_karaoke_sessions_bumped_item_id', 'karaoke_sessions', type_='foreignkey'
    )
    op.drop_column('karaoke_sessions', 'bumped_item_id')
    op.drop_constraint(
        'fk_karaoke_sessions_turn_performer_id',
        'karaoke_sessions',
        type_='foreignkey',
    )
    op.drop_column('karaoke_sessions', 'turn_performer_id')
