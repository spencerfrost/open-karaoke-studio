"""add_host_role_and_settings

Revision ID: f56ea70a4499
Revises: f1a2b3c4d5e6
Create Date: 2026-03-16 15:09:43.432444

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f56ea70a4499'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_host to users
    op.add_column('users', sa.Column('is_host', sa.Boolean(), nullable=False, server_default='false'))

    # Add host_user_id FK to karaoke_sessions
    op.add_column('karaoke_sessions', sa.Column('host_user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_karaoke_sessions_host_user_id',
        'karaoke_sessions', 'users',
        ['host_user_id'], ['id'],
        ondelete='SET NULL',
    )

    # Add status to karaoke_queue (existing rows default to "active")
    op.add_column('karaoke_queue', sa.Column('status', sa.String(), nullable=False, server_default='active'))

    # Create host_settings table
    op.create_table(
        'host_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('queue_submission_mode', sa.String(), nullable=False, server_default='instant'),
        sa.Column('max_songs_per_singer', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('queue_open', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('session_duration_hours', sa.Integer(), nullable=False, server_default='8'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )


def downgrade() -> None:
    op.drop_table('host_settings')
    op.drop_column('karaoke_queue', 'status')
    op.drop_constraint('fk_karaoke_sessions_host_user_id', 'karaoke_sessions', type_='foreignkey')
    op.drop_column('karaoke_sessions', 'host_user_id')
    op.drop_column('users', 'is_host')
