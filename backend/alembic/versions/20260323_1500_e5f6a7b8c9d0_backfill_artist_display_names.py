"""backfill_artist_display_names

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-23 15:00:00.000000

The previous migration set display_name = name (lowercase) for pre-existing
artists. This migration re-derives display_name from the original songs.artist
strings which preserve the original casing (e.g. "Bonobo" instead of "bonobo").
"""

import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FEAT_PATTERN = re.compile(r"\s+(?:ft\.?|feat\.?|featuring)\s+", re.IGNORECASE)
_SPLIT_PATTERN = re.compile(r"\s*,\s*")


def _parse(artist_str: str) -> tuple[str, list[str]]:
    parts = _FEAT_PATTERN.split(artist_str, maxsplit=1)
    primary = parts[0].strip()
    featured = (
        [a.strip() for a in _SPLIT_PATTERN.split(parts[1]) if a.strip()]
        if len(parts) > 1
        else []
    )
    return primary, featured


def upgrade() -> None:
    conn = op.get_bind()

    # Build a map: normalized artist name -> best display_name from songs
    display_names: dict[str, str] = {}

    songs = conn.execute(sa.text("SELECT DISTINCT artist FROM songs WHERE artist IS NOT NULL")).fetchall()
    for (artist_str,) in songs:
        if not artist_str:
            continue
        primary_name, featured_names = _parse(artist_str)
        for name in [primary_name] + featured_names:
            normalized = name.lower().strip()
            if normalized not in display_names:
                display_names[normalized] = name

    # Update artists whose display_name is NULL or matches the lowercase name
    for normalized, display_name in display_names.items():
        conn.execute(
            sa.text(
                "UPDATE artists SET display_name = :display_name "
                "WHERE name = :name AND (display_name IS NULL OR display_name = name)"
            ),
            {"display_name": display_name, "name": normalized},
        )


def downgrade() -> None:
    # Revert display_name back to lowercase name
    op.get_bind().execute(
        sa.text("UPDATE artists SET display_name = name")
    )
