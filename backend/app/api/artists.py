import logging
from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_admin
from app.db.database import SessionLocal
from app.db.models import User
from app.repositories.artist_repository import ArtistRepository
from app.services.artist_image_service import ArtistImageService
from app.services.file_service import FileService
from app.services.lastfm_service import LastFmService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/artists", tags=["artists"])


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class UpdateArtistRequest(BaseModel):
    display_name: str


class SetArtistImageRequest(BaseModel):
    url: str


@router.patch("/{artist_id}")
async def update_artist(
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
async def delete_artist(
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


@router.get("/image")
async def get_artist_image(name: str = Query(...)):
    """Fetch and cache artist image from Discogs, served from local disk."""
    service = ArtistImageService(FileService(), SessionLocal)
    path = await service.get_or_fetch_artist_image(name)
    if path is None:
        raise HTTPException(status_code=404, detail="Artist image not found")
    return FileResponse(str(path), media_type="image/jpeg")


@router.post("/images/backfill")
async def backfill_artist_images():
    """
    Fetch images for all artists that haven't been checked yet.
    Runs sequentially to respect Discogs rate limits (60 req/min authenticated).
    Returns counts of fetched, not_found, and errors.
    """
    db = SessionLocal()
    try:
        repo = ArtistRepository(db)
        unchecked = repo.get_all_with_image_status("not_checked")
        artist_names = [a.name for a in unchecked]
    finally:
        db.close()

    logger.info("Starting artist image backfill for %d unchecked artists", len(artist_names))

    results = {"fetched": 0, "not_found": 0, "errors": 0, "total": len(artist_names)}

    for name in artist_names:
        try:
            service = ArtistImageService(FileService(), SessionLocal)
            path = await service.get_or_fetch_artist_image(name)
            if path is not None:
                results["fetched"] += 1
            else:
                results["not_found"] += 1
        except Exception as e:
            logger.warning("Backfill error for artist %s: %s", name, e)
            results["errors"] += 1

    logger.info("Artist image backfill complete: %s", results)
    return results


@router.get("/bio")
async def get_artist_bio(name: str = Query(...), db: Session = Depends(get_db)):
    """Fetch and cache artist biography from Last.fm."""
    service = LastFmService(ArtistRepository(db))
    bio = await service.get_or_fetch_artist_bio(name)
    if bio is None:
        raise HTTPException(status_code=404, detail="Artist biography not found")
    return {"name": name, "bio": bio}


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
        raise HTTPException(status_code=422, detail="Failed to download image from the provided URL")
    return {"success": True}
