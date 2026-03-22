import httpx
import logging
import re
from pathlib import Path

from app.config import get_config
from app.repositories.artist_repository import ArtistRepository
from .file_service import FileService

logger = logging.getLogger(__name__)


def _theaudiodb_search_url() -> str:
    key = get_config().THEAUDIODB_API_KEY
    return f"https://www.theaudiodb.com/api/v1/json/{key}/search.php"


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-"))


class ArtistImageService:
    def __init__(self, file_service: FileService, artist_repo: ArtistRepository):
        self.file_service = file_service
        self.artist_repo = artist_repo

    async def get_or_fetch_artist_image(self, name: str) -> Path | None:
        artist = self.artist_repo.get_or_create(name)

        if artist.image_status == "found" and artist.image_path:
            return Path(artist.image_path)
        if artist.image_status == "not_found":
            return None

        # "not_checked" — fetch from TheAudioDB
        slug = _slugify(name)
        image_path = self.file_service.get_artist_image_path(slug)
        image_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    _theaudiodb_search_url(), params={"s": name}, timeout=10.0
                )
                resp.raise_for_status()
                artists = resp.json().get("artists")
                if not artists or not artists[0].get("strArtistThumb"):
                    self.artist_repo.update_image(
                        artist, image_path=None, status="not_found"
                    )
                    return None
                img_resp = await client.get(
                    artists[0]["strArtistThumb"], timeout=15.0
                )
                img_resp.raise_for_status()
                image_path.write_bytes(img_resp.content)
                self.artist_repo.update_image(
                    artist, image_path=str(image_path), status="found"
                )
                return image_path
        except Exception as e:
            logger.warning("Failed to fetch artist image for %s: %s", name, e)
            return None
