"""Writing a song's artist credits (the song_artists join table).

Credits arrive as a list from whatever knows the artists: YouTube Music when a
song is added from search, MusicBrainz once a recording links, or a person
editing them. The parser only runs when nothing does. set_song_credits is the
one function that writes them.
"""

import logging
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.song import DbSong
from app.db.models.song_artist import DbSongArtist
from app.repositories.artist_repository import ArtistRepository
from app.services.artist_parsing import (
    ArtistCredit,
    normalize_artist_name,
    parse_song_artists,
    parse_title_featured,
)

logger = logging.getLogger(__name__)

# Joins that might sit between two primary artists: "A & B", "A and B".
_PRIMARY_JOIN = re.compile(r"\s+(?:&|and)\s+", re.IGNORECASE)
# Patterns that strongly suggest the join is part of a band name
_BAND_JOIN = re.compile(
    r"^(?:The|His|Her|Their|Los|Las|Les|Die|Das)\s",
    re.IGNORECASE,
)


def split_known_primaries(primary: str, db: Session) -> list[str]:
    """Split a primary artist on "&" or "and" only when every half is an artist already.

    "Amber Mark & John The Blind" splits once both are in the library; "Chase &
    Status" stays whole, and "Chase & Status and Bou" splits only at "and".
    "X & The Y" is a band name and never splits.
    """
    repo = ArtistRepository(db)
    for match in _PRIMARY_JOIN.finditer(primary):
        left, right = primary[: match.start()].strip(), primary[match.end() :].strip()
        if not left or not right or _BAND_JOIN.match(right):
            continue
        if repo.find(left) and repo.find(right):
            logger.info("Split primary artist '%s' → '%s' + '%s'", primary, left, right)
            return [left, right]
    return [primary]


def parse_credits(db: Session, artist_str: str, title: str = "") -> list[ArtistCredit]:
    """Credits guessed from a song's artist text and title, for when no list is known.

    Featured artists come from the "feat." part of the artist and from a
    "(feat. X)" in the title.
    """
    primary, featured = parse_song_artists(artist_str or "")
    names = split_known_primaries(primary, db) if primary else []
    credits = [ArtistCredit(name=name, role="primary") for name in names]
    credits += [
        ArtistCredit(name=name, role="featured")
        for name in featured + parse_title_featured(title)
    ]
    return credits


def set_song_credits(
    db: Session, song: DbSong, credits: Optional[list[ArtistCredit]]
) -> None:
    """Replace a song's artist credits, and point songs.artist_id at the first primary.

    `credits` is the list whatever knows the artists gave, in order; None parses
    it from the song's artist text and title. A list with no primary makes its
    first artist primary. An artist named twice keeps their first credit.

    Never touches songs.artist. Flushes; the caller commits.
    """
    if credits is None:
        credits = parse_credits(db, song.artist or "", song.title or "")
    credits = [c for c in credits if normalize_artist_name(c.name)]
    if not credits:
        logger.warning("No artists to credit on song %s; credits unchanged", song.id)
        return
    if not any(c.role == "primary" for c in credits):
        first = credits[0]
        credits[0] = ArtistCredit(
            name=first.name,
            role="primary",
            musicbrainz_id=first.musicbrainz_id,
            youtube_music_id=first.youtube_music_id,
            credited_as=first.credited_as,
        )

    repo = ArtistRepository(db)
    resolved = []
    seen: set[int] = set()
    for credit in credits:
        artist = repo.resolve(
            credit.name,
            credit.musicbrainz_id,
            credit.youtube_music_id,
            credited_as=credit.credited_as,
        )
        if artist.id in seen:
            continue
        seen.add(artist.id)
        credited_as = credit.credited_as or credit.name
        repo.add_alias(artist, credited_as, "credited")
        resolved.append((artist, credit.role, credited_as))

    # Old rows go first: the new ones may credit the same artists.
    song.song_artists.clear()
    db.flush()
    # Primaries before featured, each in the order given.
    resolved.sort(key=lambda r: r[1] != "primary")
    for order, (artist, role, credited_as) in enumerate(resolved):
        song.song_artists.append(
            DbSongArtist(
                artist_rel=artist,
                role=role,
                display_order=order,
                credited_as=credited_as,
            )
        )
    song.artist_rel = resolved[0][0]
    db.flush()
    logger.info(
        "Credited song %s: %s",
        song.id,
        [(artist.display_name or artist.name, role) for artist, role, _ in resolved],
    )
