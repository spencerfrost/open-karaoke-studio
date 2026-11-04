"""song_singing_map

When each song's lead and backing vocals are singing, measured from its stems.
JSON in a Text column, null until measured.

Revision ID: c4e8a2f17b93
Revises: f1c6d2a8e947
Create Date: 2026-11-04 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c4e8a2f17b93"
down_revision: Union[str, None] = "f1c6d2a8e947"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("songs", sa.Column("singing_map", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("songs", "singing_map")
