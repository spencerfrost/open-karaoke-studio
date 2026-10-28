import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.config import get_config
from app.db.models.album import DbAlbum

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/albums", tags=["albums"])


@router.get("/{album_id}/cover")
def get_album_cover(album_id: int, db: Session = Depends(get_db)):
    """Serve the cached album cover art."""
    album = db.query(DbAlbum).filter(DbAlbum.id == album_id).first()

    if not album:
        raise HTTPException(status_code=404, detail=f"Album not found: {album_id}")

    if not album.cover_path:
        raise HTTPException(status_code=404, detail="Album cover not available")

    config = get_config()
    cover_file = config.library_path / album.cover_path

    if not cover_file.exists():
        logger.warning("Album cover file missing on disk: %s", cover_file)
        raise HTTPException(status_code=404, detail="Album cover file not found")

    # Without Cache-Control every view revalidates; see get_artist_image.
    return FileResponse(
        str(cover_file),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )
