"""batch_runs

One row per run of a library-wide batch job, so the admin jobs page can show
progress and the last run of each job.

Revision ID: e1c7b4a9f352
Revises: d8a3f5b2c71e
Create Date: 2026-10-09 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1c7b4a9f352'
down_revision: Union[str, None] = 'd8a3f5b2c71e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'batch_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('mode', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('celery_task_id', sa.String(), nullable=True),
        sa.Column('total', sa.Integer(), nullable=True),
        sa.Column('done', sa.Integer(), nullable=False),
        sa.Column('failed', sa.Integer(), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_batch_runs_kind', 'batch_runs', ['kind'])
    op.create_index('ix_batch_runs_status', 'batch_runs', ['status'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_batch_runs_status', table_name='batch_runs')
    op.drop_index('ix_batch_runs_kind', table_name='batch_runs')
    op.drop_table('batch_runs')
