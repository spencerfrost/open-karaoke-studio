# pylint: skip-file
"""
Make duration_ms nullable in songs table

Revision ID: d048757b81a8
Revises: addbfd875d80
Create Date: 2025-07-06 19:35:00
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d048757b81a8"
down_revision = "addbfd875d80"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
