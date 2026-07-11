"""add demo account pool fields

Revision ID: 20260710_0900_demo_pool
Revises: a2445e5aca5e
Create Date: 2026-07-10 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260710_0900_demo_pool'
down_revision: Union[str, None] = 'a2445e5aca5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users',
        sa.Column('is_demo', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column('jobs', sa.Column('session_id', sa.String(), nullable=True))
    op.add_column('jobs', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index('ix_jobs_session_id', 'jobs', ['session_id'])
    op.alter_column(
        'host_settings',
        'session_duration_hours',
        existing_type=sa.Integer(),
        type_=sa.Float(),
        existing_nullable=False,
        existing_server_default='8',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'host_settings',
        'session_duration_hours',
        existing_type=sa.Float(),
        type_=sa.Integer(),
        existing_nullable=False,
        existing_server_default='8',
        postgresql_using='round(session_duration_hours)::integer',
    )
    op.drop_index('ix_jobs_session_id', table_name='jobs')
    op.drop_column('jobs', 'user_id')
    op.drop_column('jobs', 'session_id')
    op.drop_column('users', 'is_demo')
