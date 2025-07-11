# pylint: skip-file
"""merge duration_ms and plain_lyrics migrations

Revision ID: f4e41e18858a
Revises: 20250622_duration_ms_migration, 20250707_add_plain_lyrics_column
Create Date: 2025-07-07 02:45:18.249134

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4e41e18858a"
from typing import Tuple

down_revision: Tuple[str, str] = (
    "20250622_duration_ms_migration",
    "20250707_add_plain_lyrics_column",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
