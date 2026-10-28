"""drop turns_borrowed

The turn now follows whoever sings, so nobody carries a count of turns sung
early. The downgrade re-adds the column at zero.

Revision ID: b3f7a1d9c625
Revises: e7a2c9f4b318
Create Date: 2026-10-28 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b3f7a1d9c625"
down_revision: Union[str, None] = "e7a2c9f4b318"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("session_performers") as batch_op:
        batch_op.drop_column("turns_borrowed")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "session_performers",
        sa.Column("turns_borrowed", sa.Integer(), nullable=False, server_default="0"),
    )
