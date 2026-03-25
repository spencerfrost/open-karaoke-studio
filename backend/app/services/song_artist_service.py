"""Populate the song_artists join table for a given song."""

import logging
import re

from sqlalchemy.orm import Session

from app.db.models.song import DbSong
from app.db.models.song_artist import DbSongArtist
from app.repositories.artist_repository import ArtistRepository
from app.services.artist_parsing import parse_song_artists

logger = logging.getLogger(__name__)

# Patterns that strongly suggest "&" is part of a band name, not a collaboration
_BAND_AMPERSAND = re.compile(
    r"&\s+(?:The|His|Her|Their|Los|Las|Les|Die|Das)\s",
    re.IGNORECASE,
)


def try_ampersand_split(
    credits: list[tuple[str, str]],
    db: Session,
) -> list[tuple[str, str]]:
    """If credits contain a single primary with '&', try to split using local DB knowledge.

    Only splits when BOTH sides of '&' already exist as known artists in the database.
    This avoids incorrectly splitting band names like "Bob Marley & The Wailers".
    """
    primaries = [(name, role) for name, role in credits if role == "primary"]
    if len(primaries) != 1:
        return credits  # Already split or no primary

    primary_name = primaries[0][0]
    if " & " not in primary_name:
        return credits

    # "X & The Y" is almost always a band name
    if _BAND_AMPERSAND.search(primary_name):
        return credits

    parts = [p.strip() for p in primary_name.split(" & ", 1)]
    if len(parts) != 2 or not all(parts):
        return credits

    # Check if both sides independently exist as artists in the DB
    artist_repo = ArtistRepository(db)
    a = artist_repo.get_by_name(parts[0])
    b = artist_repo.get_by_name(parts[1])

    if a and b:
        # Both exist as separate artists — split into two primaries
        featured = [(name, role) for name, role in credits if role == "featured"]
        logger.info(
            "Heuristic ampersand split: '%s' → '%s' + '%s'",
            primary_name,
            parts[0],
            parts[1],
        )
        return [(parts[0], "primary"), (parts[1], "primary")] + featured

    return credits


def populate_song_artists(db: Session, song: DbSong, artist_str: str) -> None:
    """Parse *artist_str*, create artist rows, and link them to *song* via song_artists.

    This is idempotent — existing song_artists rows for the song are deleted first.
    """
    primary_name, featured_names = parse_song_artists(artist_str)

    artist_repo = ArtistRepository(db)

    # Resolve / create the primary artist
    primary_artist = artist_repo.get_or_create(primary_name, display_name=primary_name)

    # Update the song's FK shortcut
    song.artist_id = primary_artist.id

    # Clear existing links (idempotent)
    db.query(DbSongArtist).filter(DbSongArtist.song_id == song.id).delete()

    # Insert primary
    db.add(
        DbSongArtist(
            song_id=song.id,
            artist_id=primary_artist.id,
            role="primary",
            display_order=0,
        )
    )

    # Insert featured
    for i, feat_name in enumerate(featured_names, start=1):
        feat_artist = artist_repo.get_or_create(feat_name, display_name=feat_name)
        db.add(
            DbSongArtist(
                song_id=song.id,
                artist_id=feat_artist.id,
                role="featured",
                display_order=i,
            )
        )

    db.commit()
    logger.info(
        "Populated song_artists for song %s: primary=%s, featured=%s",
        song.id,
        primary_name,
        featured_names,
    )
