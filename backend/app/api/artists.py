import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_admin
from app.db.database import SessionLocal
from app.db.models import User
from app.db.models.song import DbSong
from app.db.models.song_artist import DbSongArtist
from app.repositories.artist_repository import ArtistRepository
from app.schemas.song import SplitArtistCreditsRequest
from app.services.artist_image_service import ArtistImageService
from app.services.artist_parsing import ArtistCredit, credit_line
from app.services.file_service import FileService
from app.services.song_artist_service import set_song_credits

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/artists", tags=["artists"])


class UpdateArtistRequest(BaseModel):
    display_name: str


class SetArtistImageRequest(BaseModel):
    url: str


@router.patch("/{artist_id}")
def update_artist(
    artist_id: int,
    body: UpdateArtistRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update an artist's display name. Requires admin."""
    repo = ArtistRepository(db)
    artist = repo.get_by_id(artist_id)
    if artist is None:
        raise HTTPException(status_code=404, detail="Artist not found")
    artist = repo.update_display_name(artist, body.display_name)
    return {"id": artist.id, "name": artist.name, "display_name": artist.display_name}


@router.delete("/{artist_id}")
def delete_artist(
    artist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Delete an artist. Songs exclusively linked to this artist are also deleted.
    Songs shared with other artists have only this artist's credit removed.
    Requires admin.
    """
    repo = ArtistRepository(db)
    artist = repo.get_by_id(artist_id)
    if artist is None:
        raise HTTPException(status_code=404, detail="Artist not found")
    result = repo.delete_with_cascade(artist)
    return result


@router.get("/{artist_id}/image")
async def get_artist_image(artist_id: int):
    """Fetch and cache artist image from Discogs, served from local disk."""
    service = ArtistImageService(FileService(), SessionLocal)
    path = await service.get_or_fetch_artist_image(artist_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Artist image not found")
    # Cached for an hour so the stage wheel can scroll back over an artist
    # without asking again. Short enough that a replaced photo shows up the
    # same evening; the edit dialog busts it at once with ?v=.
    return FileResponse(
        str(path),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/{artist_id}/images/search")
async def search_artist_images(
    artist_id: int,
    q: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Return Discogs image candidates for an artist without downloading them."""
    repo = ArtistRepository(db)
    artist = repo.get_by_id(artist_id)
    if artist is None:
        raise HTTPException(status_code=404, detail="Artist not found")
    service = ArtistImageService(FileService(), SessionLocal)
    candidates = await service.search_artist_images(q)
    return {"results": candidates}


@router.post("/{artist_id}/image")
async def set_artist_image(
    artist_id: int,
    body: SetArtistImageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Download and save an artist image from the given URL."""
    repo = ArtistRepository(db)
    artist = repo.get_by_id(artist_id)
    if artist is None:
        raise HTTPException(status_code=404, detail="Artist not found")
    service = ArtistImageService(FileService(), SessionLocal)
    path = await service.set_image_from_url(artist_id, body.url)
    if path is None:
        raise HTTPException(
            status_code=422, detail="Failed to download image from the provided URL"
        )
    return {"success": True}


@router.post("/{artist_id}/split-credits")
def split_artist_credits(
    artist_id: int,
    body: SplitArtistCreditsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Manually split a combined artist (e.g. "A & B") into separate credits.

    On every song crediting this artist, the given credits take its place and
    the song's other credits stay. Where it was featured, they're all
    featured. The artist text is rebuilt from the new credits and the song is
    confirmed. Requires admin.
    """
    repo = ArtistRepository(db)
    artist = repo.get_by_id(artist_id)
    if artist is None:
        raise HTTPException(status_code=404, detail="Artist not found")

    if not any(c.role == "primary" for c in body.credits):
        raise HTTPException(
            status_code=400, detail="At least one primary credit is required"
        )

    songs = (
        db.query(DbSong)
        .join(DbSongArtist, DbSongArtist.song_id == DbSong.id)
        .filter(DbSongArtist.artist_id == artist_id)
        .all()
    )

    now = datetime.now(timezone.utc)
    for song in songs:
        credits: list[ArtistCredit] = []
        for link in sorted(song.song_artists, key=lambda c: c.display_order):
            if link.artist_id != artist_id:
                credits.append(_credit_of(link))
                continue
            credits += [
                ArtistCredit(
                    name=c.name,
                    role=c.role if link.role == "primary" else "featured",
                )
                for c in body.credits
            ]
        set_song_credits(db, song, credits)
        song.artist = credit_line([(c.credited_as or c.name, c.role) for c in credits])
        song.metadata_confirmed_at = now

    # The combined artist usually has nothing left.
    db.flush()
    db.expire(artist)
    repo.delete_if_unused(artist)
    db.commit()
    return {"updated": len(songs)}


@router.post("/{artist_id}/merge-into/{target_id}")
def merge_artist(
    artist_id: int,
    target_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Merge one artist into another: "Jay‐Z" into "Jay-Z".

    Moves every credit to the target, repoints songs and albums, keeps the
    source's names and ids on the target as aliases, and deletes the source.
    Songs' artist text is left as it is. Requires admin.
    """
    if artist_id == target_id:
        raise HTTPException(status_code=400, detail="An artist can't merge into itself")
    repo = ArtistRepository(db)
    source = repo.get_by_id(artist_id)
    target = repo.get_by_id(target_id)
    if source is None or target is None:
        raise HTTPException(status_code=404, detail="Artist not found")

    source_name = source.display_name or source.name
    moved = repo.merge_into(source, target)
    db.commit()
    logger.info(
        "Merged artist %s (%s) into %s (%s): %d credits",
        artist_id,
        source_name,
        target_id,
        target.display_name or target.name,
        moved,
    )
    return {
        "id": target.id,
        "name": target.display_name or target.name,
        "moved": moved,
    }


def _credit_of(link: DbSongArtist) -> ArtistCredit:
    """A song's existing credit, as set_song_credits takes it."""
    artist = link.artist_rel
    return ArtistCredit(
        name=artist.display_name or artist.name,
        role=link.role,
        musicbrainz_id=artist.musicbrainz_artist_id,
        youtube_music_id=artist.youtube_music_artist_id,
        credited_as=link.credited_as,
    )
