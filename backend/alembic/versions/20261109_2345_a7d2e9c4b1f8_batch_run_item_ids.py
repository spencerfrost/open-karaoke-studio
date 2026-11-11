"""batch_run_item_ids

The songs (or artists) a batch run works through, in order, so a run the
worker stopped can carry on from where it got to.

Revision ID: a7d2e9c4b1f8
Revises: d9b3f6a2c1e5
Create Date: 2026-11-09 23:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a7d2e9c4b1f8"
down_revision: Union[str, None] = "d9b3f6a2c1e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("batch_runs", sa.Column("item_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("batch_runs", "item_ids")
