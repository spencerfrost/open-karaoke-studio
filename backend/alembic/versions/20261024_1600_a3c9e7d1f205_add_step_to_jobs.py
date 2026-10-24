"""Add step to jobs table

The pipeline step a job is on (download, separate, align), written by Celery next
to progress so clients don't infer it from status and message text.

Revision ID: a3c9e7d1f205
Revises: c5f8a2e7d394
Create Date: 2026-10-24 16:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3c9e7d1f205"
down_revision: Union[str, None] = "c5f8a2e7d394"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("jobs", sa.Column("step", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("jobs", "step")
