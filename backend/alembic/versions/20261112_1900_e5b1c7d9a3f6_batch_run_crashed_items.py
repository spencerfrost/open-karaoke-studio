"""batch_run_crashed_items

The song a batch task is working on, so a song that kills its worker is
counted failed on resume instead of crashing every worker that picks the run
up, and the songs that did.

Revision ID: e5b1c7d9a3f6
Revises: d3a7e9c1f5b2
Create Date: 2026-11-12 19:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e5b1c7d9a3f6"
down_revision: Union[str, None] = "d3a7e9c1f5b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("batch_runs") as batch_op:
        batch_op.add_column(sa.Column("item_started", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("crashed_item_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("batch_runs") as batch_op:
        batch_op.drop_column("crashed_item_ids")
        batch_op.drop_column("item_started")
