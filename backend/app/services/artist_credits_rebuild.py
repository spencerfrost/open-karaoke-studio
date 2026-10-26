"""The artist credits rebuild: re-credit the library and tidy the artist list.

One pass over the whole library, run from the admin Jobs page. It

1. credits every song with a recording from its MusicBrainz credits,
   including confirmed songs (their credits are the old parser's guess from
   the text, not a list a person picked), and re-parses songs without one
   whose credits the old code wrote;
2. records MusicBrainz's aliases for every artist with an MB id;
3. merges rows for the same artist: an MB alias or the same name once
   normalized ("Jay‐Z" and "Jay-Z", "&" and "and", case);
4. names artists with MusicBrainz's current name, and lowercase rows with the
   spelling their credits print;
5. deletes artists nothing refers to.

It returns a report of what changed. The MusicBrainz lookups happen first, in
fetch_musicbrainz, so the database work runs in one transaction that a
preview rolls back.
"""

import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from sqlalchemy.orm import Session, selectinload

from app.db.models import DbArtist, DbArtistAlias, DbSong, DbSongArtist
from app.repositories.artist_repository import ArtistRepository
from app.services.artist_parsing import (
    ArtistCredit,
    normalize_artist_name,
    parse_song_artists,
    parse_title_featured,
)
from app.services.song_artist_service import set_song_credits

logger = logging.getLogger(__name__)

# How many example rows each report list keeps; the counts are always whole.
REPORT_LIMIT = 2000

_PRIMARY_JOIN = re.compile(r"\s(?:&|and)\s", re.IGNORECASE)


@dataclass
class MusicBrainzData:
    """What the rebuild needs from MusicBrainz, fetched before it starts."""

    # Recording id → its credits; None where the lookup failed.
    recordings: dict[str, Optional[list[ArtistCredit]]] = field(default_factory=dict)
    # MB artist id → [current name, aliases...]; None where the lookup failed.
    artists: dict[str, Optional[list[str]]] = field(default_factory=dict)


def fetch_musicbrainz(
    session: Session,
    cache_dir: Optional[Path],
    on_total: Callable[[int], None] = lambda total: None,
    on_step: Callable[[], None] = lambda: None,
) -> MusicBrainzData:
    """Look up every linked recording, then every artist those credit or the
    library already ties to an MB id.

    Progress: `on_total` gets the number of steps (songs, then songs plus
    artists once those are known); `on_step` is called after each.
    """
    from app.services.musicbrainz_service import (
        get_artist_aliases,
        get_recording_details,
    )

    data = MusicBrainzData()
    recording_ids = [
        recording_id
        for (recording_id,) in session.query(DbSong.musicbrainz_recording_id)
    ]
    on_total(len(recording_ids))
    for recording_id in recording_ids:
        if recording_id and recording_id not in data.recordings:
            _show, credits = get_recording_details(recording_id, cache_dir)
            data.recordings[recording_id] = credits
        on_step()

    mbids = {
        c.musicbrainz_id
        for credits in data.recordings.values()
        for c in credits or []
        if c.musicbrainz_id
    }
    mbids |= {
        mbid
        for (mbid,) in session.query(DbArtist.musicbrainz_artist_id).filter(
            DbArtist.musicbrainz_artist_id.isnot(None)
        )
    }
    on_total(len(recording_ids) + len(mbids))
    for mbid in sorted(mbids):
        data.artists[mbid] = get_artist_aliases(mbid, cache_dir)
        on_step()
    return data


def rebuild(session: Session, mb: MusicBrainzData) -> dict:
    """Make every change and return the report. Flushes; the caller commits
    (apply) or rolls back (preview)."""
    repo = ArtistRepository(session)
    report: dict = {"before": library_numbers(session)}

    report["songs"] = _recredit_songs(session, mb)
    _add_musicbrainz_aliases(session, repo, mb)
    # Each step flushes; expiring between them reloads the collections the
    # step before changed under them.
    session.expire_all()
    report["merges"] = _merge_duplicates(session, repo, mb)
    session.expire_all()
    report["renames"] = _rename_artists(session, repo, mb)
    report["deleted"] = _delete_unused(session, repo)
    session.expire_all()
    report["unsure"] = _unsure_songs(session)
    report["disagree"] = _disagreeing_songs(session)
    report["after"] = library_numbers(session)
    return report


# ---------------------------------------------------------------------------
# 1. Credits
# ---------------------------------------------------------------------------


def _credit_list(song: DbSong) -> list[dict]:
    return [
        {
            "name": link.artist_rel.display_name or link.artist_rel.name,
            "role": link.role,
        }
        for link in sorted(song.song_artists, key=lambda link: link.display_order)
    ]


def _written_by_old_code(song: DbSong) -> bool:
    """Credits from before credits came as lists: none, or no credited name kept."""
    return not song.song_artists or any(
        link.credited_as is None for link in song.song_artists
    )


def _recredit_songs(session: Session, mb: MusicBrainzData) -> dict:
    changed: list[dict] = []
    counts = Counter()
    songs = (
        session.query(DbSong)
        .options(selectinload(DbSong.song_artists).joinedload(DbSongArtist.artist_rel))
        .order_by(DbSong.id)
        .all()
    )
    for song in songs:
        recording_credits = (
            mb.recordings.get(song.musicbrainz_recording_id)
            if song.musicbrainz_recording_id
            else None
        )
        if recording_credits:
            source = "recording"
            credits: Optional[list[ArtistCredit]] = recording_credits
        elif _written_by_old_code(song):
            source = "parsed"
            credits = None
        else:
            counts["kept"] += 1
            continue
        if song.musicbrainz_recording_id and not recording_credits:
            counts["lookup_failed"] += 1

        before = _credit_list(song)
        set_song_credits(session, song, credits)
        after = _credit_list(song)
        counts[source] += 1
        if before != after:
            counts["changed"] += 1
            if len(changed) < REPORT_LIMIT:
                changed.append(
                    {
                        "songId": song.id,
                        "title": song.title,
                        "artist": song.artist,
                        "confirmed": song.metadata_confirmed_at is not None,
                        "source": source,
                        "before": before,
                        "after": after,
                    }
                )
    return {"counts": dict(counts), "changed": changed}


# ---------------------------------------------------------------------------
# 2–4. Aliases, merges, names
# ---------------------------------------------------------------------------


def _artists_by_mbid(session: Session) -> dict[str, DbArtist]:
    return {
        a.musicbrainz_artist_id: a
        for a in session.query(DbArtist).filter(
            DbArtist.musicbrainz_artist_id.isnot(None)
        )
    }


def _add_musicbrainz_aliases(
    session: Session, repo: ArtistRepository, mb: MusicBrainzData
) -> None:
    """MB's names for each artist, then every row's own name, as aliases."""
    for mbid, artist in _artists_by_mbid(session).items():
        for name in mb.artists.get(mbid) or []:
            repo.add_alias(artist, name, "musicbrainz")
    for artist in session.query(DbArtist).all():
        repo.add_alias(artist, artist.display_name or artist.name, "credited")


def _link_count(session: Session, artist: DbArtist) -> int:
    return (
        session.query(DbSongArtist).filter(DbSongArtist.artist_id == artist.id).count()
    )


def _merge_duplicates(
    session: Session, repo: ArtistRepository, mb: MusicBrainzData
) -> list[dict]:
    """Merge rows naming one artist. Two rows with different MB ids never merge."""
    merges: list[dict] = []

    def merge(source: DbArtist, target: DbArtist, reason: str) -> None:
        entry = {
            "from": source.display_name or source.name,
            "into": target.display_name or target.name,
            "reason": reason,
        }
        entry["credits"] = repo.merge_into(source, target)
        merges.append(entry)

    # Every key an MB artist goes by: their names on MusicBrainz and their row.
    owner: dict[str, Optional[DbArtist]] = {}
    for mbid, artist in _artists_by_mbid(session).items():
        names = (mb.artists.get(mbid) or []) + [artist.display_name or artist.name]
        for key in {normalize_artist_name(n) for n in names} - {""}:
            # A key two MB artists share names neither for sure.
            owner[key] = None if owner.get(key, artist) is not artist else artist

    for artist in session.query(DbArtist).order_by(DbArtist.id).all():
        if artist.musicbrainz_artist_id:
            continue
        target = owner.get(normalize_artist_name(artist.display_name or artist.name))
        if target is not None:
            merge(artist, target, "musicbrainz")

    # Rows with no MB id that share a normalized name.
    groups: dict[str, list[DbArtist]] = defaultdict(list)
    for artist in session.query(DbArtist).order_by(DbArtist.id).all():
        key = normalize_artist_name(artist.display_name or artist.name)
        if key and not artist.musicbrainz_artist_id:
            groups[key].append(artist)
    for rows in groups.values():
        if len(rows) < 2:
            continue
        # The row most songs already use stays.
        target = max(rows, key=lambda a: (_link_count(session, a), -a.id))
        for artist in rows:
            if artist is not target:
                merge(artist, target, "spelling")
    return merges


def _rename_artists(
    session: Session, repo: ArtistRepository, mb: MusicBrainzData
) -> list[dict]:
    """MusicBrainz's current name where there is one. A lowercase row without
    one takes the spelling its credits print most."""
    renames: list[dict] = []
    for artist in session.query(DbArtist).order_by(DbArtist.id).all():
        current = artist.display_name or artist.name
        names = mb.artists.get(artist.musicbrainz_artist_id or "") or []
        new = names[0] if names else None
        if new is None and current == current.lower():
            printed = Counter(
                link.credited_as
                for link in artist.song_artist_links
                if link.credited_as and link.credited_as != link.credited_as.lower()
            )
            new = printed.most_common(1)[0][0] if printed else None
        if not new or new == current:
            continue

        artist.display_name = new
        # The stored key follows the name, unless another row has it.
        if not repo.get_by_name(new):
            artist.name = new.lower()
        repo.add_alias(artist, new, "credited")
        renames.append({"from": current, "to": new})
    session.flush()
    return renames


# ---------------------------------------------------------------------------
# 5. Cleanup and the report's lists
# ---------------------------------------------------------------------------


def _delete_unused(session: Session, repo: ArtistRepository) -> dict:
    names = []
    for artist in session.query(DbArtist).order_by(DbArtist.id).all():
        name = artist.display_name or artist.name
        if repo.delete_if_unused(artist):
            names.append(name)
    return {"count": len(names), "names": names[:REPORT_LIMIT]}


def _song_row(song: DbSong) -> dict:
    return {
        "songId": song.id,
        "title": song.title,
        "artist": song.artist,
        "credits": _credit_list(song),
    }


def _unsure_songs(session: Session) -> dict:
    """Songs without a recording whose primary artist has "&" or "and" in it:
    the parser leaves those whole unless both halves are artists."""
    rows = []
    for song in session.query(DbSong).filter(DbSong.musicbrainz_recording_id.is_(None)):
        primaries = [
            link.artist_rel.display_name or link.artist_rel.name
            for link in song.song_artists
            if link.role == "primary"
        ]
        if any(_PRIMARY_JOIN.search(name) for name in primaries):
            rows.append(_song_row(song))
    rows.sort(key=lambda r: (r["artist"] or "").lower())
    return {"count": len(rows), "songs": rows[:REPORT_LIMIT]}


def credits_match_text(song: DbSong) -> bool:
    """Whether a song's artist text names its primary credit.

    The text's primary part matches a credited name (as filed or as printed),
    or all the primaries joined: "Amber Mark & John The Blind" credited as two.
    """
    primary, _ = parse_song_artists(song.artist or "")
    expected = normalize_artist_name(primary)
    if not expected:
        return True
    names: list[str] = []
    primaries: list[str] = []
    for link in sorted(song.song_artists, key=lambda link: link.display_order):
        filed = link.artist_rel.display_name or link.artist_rel.name
        names += [filed, link.credited_as or filed]
        names += [alias.name for alias in link.artist_rel.aliases]
        if link.role == "primary":
            primaries.append(link.credited_as or filed)
    for joiner in (" & ", " and ", ", "):
        names.append(joiner.join(primaries))
    return any(normalize_artist_name(n) == expected for n in names)


def _disagreeing_songs(session: Session) -> dict:
    rows = [
        _song_row(song)
        for song in session.query(DbSong).order_by(DbSong.artist)
        if song.song_artists and not credits_match_text(song)
    ]
    return {"count": len(rows), "songs": rows[:REPORT_LIMIT]}


def library_numbers(session: Session) -> dict:
    """The numbers the plan's "Why" counts, recounted."""
    songs = session.query(DbSong).count()
    artists = session.query(DbArtist).count()
    linked = session.query(DbSongArtist.artist_id).distinct().count()

    roles: dict[int, set[str]] = defaultdict(set)
    featured_songs: Counter = Counter()
    grouped_guests = 0
    for artist_id, role, display_name, name in (
        session.query(
            DbSongArtist.artist_id,
            DbSongArtist.role,
            DbArtist.display_name,
            DbArtist.name,
        )
        .join(DbArtist, DbArtist.id == DbSongArtist.artist_id)
        .all()
    ):
        roles[artist_id].add(role)
        if role == "featured":
            featured_songs[artist_id] += 1
            if _PRIMARY_JOIN.search(display_name or name):
                grouped_guests += 1
    featured_only = [a for a, r in roles.items() if r == {"featured"}]

    feat_in_title = sum(
        1
        for (title,) in session.query(DbSong.title)
        if parse_title_featured(title or "")
    )
    with_recording = (
        session.query(DbSong)
        .filter(DbSong.musicbrainz_recording_id.isnot(None))
        .count()
    )
    return {
        "songs": songs,
        "songsWithRecording": with_recording,
        "artists": artists,
        "artistsLinked": linked,
        "artistsLinkedToNothing": artists - linked,
        "featuredOnly": len(featured_only),
        "featuredOnlyOnOneSong": sum(
            1 for a in featured_only if featured_songs[a] == 1
        ),
        "groupedGuestCredits": grouped_guests,
        "featInTitle": feat_in_title,
        "aliases": session.query(DbArtistAlias).count(),
    }
