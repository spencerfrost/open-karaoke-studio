"""add performer consecutive passes

Adds `session_performers.consecutive_passes`, the counter behind unit 4's
auto-pass (see docs/plans/2026-08-29-handoff-screen.md). The handoff screen
offers the turn to whoever is next in the circle; if nobody steps up before the
timer expires, the turn passes forward one lap. Without a counter that pass
repeats forever - a roster of three people who have all gone home would cycle
every 45 seconds all night - so two consecutive passes deactivate the seat.

Existing rows start at 0: nobody has been passed over yet, and any activity
(queueing, claiming a turn, a song starting) resets it anyway.

Revision ID: c4e7a95d31b8
Revises: b8f3e1a2c9d4
Create Date: 2026-08-31 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e7a95d31b8"
down_revision: Union[str, None] = "b8f3e1a2c9d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "session_performers",
        sa.Column(
            "consecutive_passes", sa.Integer(), nullable=False, server_default="0"
        ),
    )


def downgrade() -> None:
    op.drop_column("session_performers", "consecutive_passes")
