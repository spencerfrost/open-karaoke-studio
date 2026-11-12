"""
Adding songs from YouTube: what's already in the library, and adding one.

The add-song flow shows each YouTube Music result with its library state and
adds one in a single request. Both sides use the same matching rule, so the
button a guest sees and what the add does always agree:

- A library song matches a result when it has the same video id, or the same
  artist and title (case-insensitive).
- A working copy (processed or still processing) means the song is there.
- A failed copy, when it's the only one, is restarted instead of adding a
  duplicate beside it.
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from fastapi import HTTPException
from sqlalchemy import func, tuple_
from sqlalchemy.orm import Session

from app.api.dependencies import RequesterContext
from app.db.models import JobStep
from app.db.models.song import DbSong
from app.repositories.song_repository import SongRepository
from app.services.artist_parsing import ArtistCredit, artist_credit
from app.services.demo_service import enforce_demo_download_quota
from app.services.file_service import FileService
from app.utils.owner_tag import session_owner_tag

logger = logging.getLogger(__name__)

LibraryStatus = Literal["ready", "processing", "failed"]


# --------------------------------------------------------------------------
# What's already in the library
# --------------------------------------------------------------------------


def _artist_title_pairs(song: Dict[str, Any]) -> set[tuple[str, str]]:
    """The (artist, title) spellings a library copy of this song could have.

    Its full credit line, as an add stores it now, and its first artist alone,
    as songs added before multiple artists were kept were stored.
    """
    title = (song.get("title") or "").strip().lower()
    names = [a["name"] for a in song.get("artists") or [] if a.get("name")]
    if not title or not names:
        return set()
    return {(artist_credit(names).lower(), title), (names[0].strip().lower(), title)}


def _entry(rows: List[tuple[str, str]]) -> Optional[Dict[str, Any]]:
    """The library entry for a song's matching (id, status) rows, best first."""
    for song_id, status in rows:
        if status == "processed":
            return {"status": "ready", "songId": song_id}
    for song_id, status in rows:
        if status != "error":
            return {"status": "processing", "songId": song_id}
    if rows:
        return {"status": "failed", "songId": rows[0][0]}
    return None


def attach_library_entries(db: Session, songs: List[Dict[str, Any]]) -> None:
    """Set each song's `library` field: its library copy's state, or None.

    Two queries for the whole list: one by video id, one by artist and title.
    Video id matches come first, so a failed exact copy is the one restarted.
    """
    if not songs:
        return

    video_ids = {s["videoId"] for s in songs if s.get("videoId")}
    pairs = set().union(*(_artist_title_pairs(s) for s in songs))

    by_video_id: dict[str, list[tuple[str, str]]] = {}
    if video_ids:
        for song_id, video_id, status in (
            db.query(DbSong.id, DbSong.video_id, DbSong.status)
            .filter(DbSong.video_id.in_(video_ids))
            .order_by(DbSong.date_added)
            .all()
        ):
            by_video_id.setdefault(video_id, []).append((song_id, status))

    by_pair: dict[tuple[str, str], list[tuple[str, str]]] = {}
    if pairs:
        artist_lower = func.lower(DbSong.artist)
        title_lower = func.lower(DbSong.title)
        for song_id, artist, title, status in (
            db.query(DbSong.id, artist_lower, title_lower, DbSong.status)
            .filter(tuple_(artist_lower, title_lower).in_(pairs))
            .order_by(DbSong.date_added)
            .all()
        ):
            by_pair.setdefault((artist, title), []).append((song_id, status))

    for song in songs:
        rows = list(by_video_id.get(song.get("videoId") or "", []))
        for pair in _artist_title_pairs(song):
            rows += [r for r in by_pair.get(pair, []) if r not in rows]
        song["library"] = _entry(rows)


# --------------------------------------------------------------------------
# Creating songs and queueing downloads
# --------------------------------------------------------------------------


def create_song_record(
    db: Session,
    song_data: Dict[str, Any],
    credits: Optional[List[ArtistCredit]] = None,
) -> DbSong:
    """Create a library song, link its artists, and make its directory.

    `credits` is the artist list the song came with; without one they're
    parsed from its artist text and title.
    """
    from app.services.song_artist_service import set_song_credits

    song_data = {**song_data, "id": song_data.get("id") or str(uuid.uuid4())}
    logger.info("Creating new song with ID: %s", song_data["id"])

    song = SongRepository(db).create(song_data)
    set_song_credits(db, song, credits)
    db.commit()

    try:
        song_dir = FileService().get_song_directory(song.id)
        song_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Created directory for song: %s", song_dir)
    except Exception as e:
        logger.warning("Error creating directory for song %s: %s", song.id, e)

    return song


def queue_youtube_download(
    *,
    song_id: str,
    video_id: str,
    artist: str,
    title: str,
    engine_type: str,
    session_id: Optional[str],
    user_id: Optional[int],
) -> str:
    """Queue the download and processing job for a song; returns the job id."""
    from app.services.youtube_service import YouTubeService

    job_id = YouTubeService().download_and_process_async(
        song_id=song_id,
        video_id_or_url=video_id,
        artist=artist,
        title=title,
        engine_type=engine_type,
        session_id=session_id,
        user_id=user_id,
    )
    logger.info(
        "YouTube processing started for song %s, video %s, job %s",
        song_id,
        video_id,
        job_id,
    )
    return job_id


def restart_youtube_processing(
    song_repo: SongRepository,
    song_id: str,
    *,
    video_id: str,
    title: str,
    artist: str,
    engine_type: str,
    session_id: Optional[str] = None,
    user_id: Optional[int] = None,
) -> str:
    """Clear a song's processing results and files, then queue a fresh download.

    Shared by replace-youtube (admin, possibly a new source), retry (guest,
    same source) and adding a song whose only copy failed. Returns the new job
    id; 409 if the song already has a job.
    """
    from app.repositories import JobRepository

    active_jobs = JobRepository().get_in_flight_jobs()
    if any(j.song_id == song_id for j in active_jobs):
        raise HTTPException(status_code=409, detail="Song is already being processed")

    song_repo.update(
        song_id,
        status="processing",
        error_message=None,
        video_id=video_id,
        acoustid_fingerprint_status="not_checked",
        acoustid_score=None,
        musicbrainz_recording_id=None,
        acoustid_suggested_recording_id=None,
        acoustid_suggested_title=None,
        acoustid_suggested_artist=None,
        vocal_range_low=None,
        vocal_range_high=None,
        loudness_lufs=None,
        true_peak_dbtp=None,
        gain_db=None,
        engine_type=None,
    )

    FileService().delete_song_files(song_id)

    return queue_youtube_download(
        song_id=song_id,
        video_id=video_id,
        artist=artist,
        title=title,
        engine_type=engine_type,
        session_id=session_id,
        user_id=user_id,
    )


def job_created_event(
    *,
    job_id: str,
    song_id: str,
    artist: Optional[str],
    title: Optional[str],
    session_id: Optional[str],
) -> Dict[str, Any]:
    """The job a `job_created` broadcast carries for a newly queued download."""
    return {
        "id": job_id,
        "song_id": song_id,
        "status": "pending",
        "step": JobStep.DOWNLOAD.value,
        "progress": 0,
        "artist": artist,
        "title": title,
        "owner_tag": session_owner_tag(session_id),
    }


# --------------------------------------------------------------------------
# Adding a song in one request
# --------------------------------------------------------------------------


@dataclass
class YouTubeAdd:
    """What adding a song did: the song it's on, its job, and the broadcast."""

    song_id: str
    job_id: str
    restarted: bool
    event: Dict[str, Any]


def add_song_from_youtube(
    db: Session,
    requester: RequesterContext,
    *,
    video_id: str,
    title: str,
    artists: List[Dict[str, Optional[str]]],
    album: Optional[str] = None,
    duration: Optional[float] = None,
    source: str = "youtube_music",
    engine_type: str = "three_track",
) -> YouTubeAdd:
    """Add a YouTube song to the library and queue its processing.

    `artists` is the result's artist list ({name, id}), primary first; the
    song is credited from it as given. A YouTube Music id is kept only for
    YouTube Music results: a plain video's channel isn't an artist page.

    Restarts the song's failed copy when that's the only one, so trying again
    never makes a duplicate. 409 when a working copy is already there.
    """
    # Counts against demo download quotas once. No-op for everyone else.
    session_id, user_id = enforce_demo_download_quota(db, requester)

    artist = artist_credit([a["name"] for a in artists])
    candidate = {"videoId": video_id, "title": title, "artists": artists}
    attach_library_entries(db, [candidate])
    entry = candidate["library"]

    if entry and entry["status"] != "failed":
        raise HTTPException(
            status_code=409, detail="This song is already in the songbook"
        )

    if entry:
        song_id = entry["songId"]
        logger.info("Restarting failed song %s instead of adding a duplicate", song_id)
        job_id = restart_youtube_processing(
            SongRepository(db),
            song_id,
            video_id=video_id,
            artist=artist,
            title=title,
            engine_type=engine_type,
            session_id=session_id,
            user_id=user_id,
        )
    else:
        song = create_song_record(
            db,
            {
                "title": title,
                "artist": artist,
                "album": album,
                "duration": duration,
                "source": source,
                "video_id": video_id,
            },
            credits=[
                ArtistCredit(
                    name=a["name"],
                    role="primary" if i == 0 else "featured",
                    youtube_music_id=(
                        a.get("id") if source == "youtube_music" else None
                    ),
                )
                for i, a in enumerate(artists)
            ],
        )
        song_id = song.id
        job_id = queue_youtube_download(
            song_id=song_id,
            video_id=video_id,
            artist=artist,
            title=title,
            engine_type=engine_type,
            session_id=session_id,
            user_id=user_id,
        )

    return YouTubeAdd(
        song_id=song_id,
        job_id=job_id,
        restarted=entry is not None,
        event=job_created_event(
            job_id=job_id,
            song_id=song_id,
            artist=artist,
            title=title,
            session_id=session_id,
        ),
    )
