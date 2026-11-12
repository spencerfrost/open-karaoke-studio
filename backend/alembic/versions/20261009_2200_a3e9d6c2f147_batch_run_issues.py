"""batch_runs issues

How many problems a hand-run scan (disk check, metadata, duplicates) found,
so the admin overview can show its last result without scanning again.

Revision ID: a3e9d6c2f147
Revises: f2d8c5a1b6e3
Create Date: 2026-10-09 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3e9d6c2f147'
down_revision: Union[str, None] = 'f2d8c5a1b6e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('batch_runs', sa.Column('issues', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('batch_runs', 'issues')
