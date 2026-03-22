import logging
from typing import Generator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.repositories.artist_repository import ArtistRepository
from app.services.artist_image_service import ArtistImageService
from app.services.file_service import FileService

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
    """Fetch and cache artist thumbnail from TheAudioDB, served from local disk."""
    service = ArtistImageService(FileService(), ArtistRepository(db))
    path = await service.get_or_fetch_artist_image(name)
    if path is None:
        raise HTTPException(status_code=404, detail="Artist image not found")
    return FileResponse(str(path), media_type="image/jpeg")
