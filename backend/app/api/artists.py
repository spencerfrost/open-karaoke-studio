import logging
from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
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


@router.get("/image")
async def get_artist_image(name: str = Query(...), db: Session = Depends(get_db)):
    """Fetch and cache artist image from Discogs, served from local disk."""
    service = ArtistImageService(FileService(), ArtistRepository(db))
    path = await service.get_or_fetch_artist_image(name)
    if path is None:
        raise HTTPException(status_code=404, detail="Artist image not found")
    return FileResponse(str(path), media_type="image/jpeg")


@router.post("/images/backfill")
async def backfill_artist_images(db: Session = Depends(get_db)):
    """
    Fetch images for all artists that haven't been checked yet.
    Runs sequentially to respect Discogs rate limits (60 req/min authenticated).
    Returns counts of fetched, not_found, and errors.
    """
    repo = ArtistRepository(db)
    unchecked = repo.get_all_with_image_status("not_checked")
    logger.info("Starting artist image backfill for %d unchecked artists", len(unchecked))

    results = {"fetched": 0, "not_found": 0, "errors": 0, "total": len(unchecked)}

    for artist in unchecked:
        try:
            service = ArtistImageService(FileService(), repo)
            path = await service.get_or_fetch_artist_image(artist.name)
            if path is not None:
                results["fetched"] += 1
            else:
                results["not_found"] += 1
        except Exception as e:
            logger.warning("Backfill error for artist %s: %s", artist.name, e)
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
