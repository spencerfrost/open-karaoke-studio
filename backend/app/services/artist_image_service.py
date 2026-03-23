import asyncio
import logging
import re
from pathlib import Path

import httpx

from app.config import get_config
from app.repositories.artist_repository import ArtistRepository

from .file_service import FileService

logger = logging.getLogger(__name__)

_DISCOGS_USER_AGENT = "OpenKaraokeStudio/1.0 +https://github.com/open-karaoke-studio"

# Discogs allows 60 req/min for authenticated requests (moving average window).
# We use a semaphore to limit concurrent outbound requests, plus we inspect the
# X-Discogs-Ratelimit-Remaining header and sleep when the budget runs low.
_DISCOGS_SEMAPHORE = asyncio.Semaphore(3)
_DISCOGS_RATE_LIMIT_LOW = 5  # sleep when remaining budget falls to this value
_DISCOGS_RATE_LIMIT_SLEEP = 2.0  # seconds to sleep when budget is low


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

        # "not_checked" — fetch from Discogs
        slug = _slugify(name)
        image_path = self.file_service.get_artist_image_path(slug)
        image_path.parent.mkdir(parents=True, exist_ok=True)

        token = get_config().DISCOGS_TOKEN
        headers = {
            "Authorization": f"Discogs token={token}",
            "User-Agent": _DISCOGS_USER_AGENT,
        }

        try:
            async with _DISCOGS_SEMAPHORE:
                async with httpx.AsyncClient() as client:
                    # Step 1: search for artist to get Discogs artist ID
                    search_resp = await client.get(
                        "https://api.discogs.com/database/search",
                        params={"q": name, "type": "artist"},
                        headers=headers,
                        timeout=10.0,
                    )
                    search_resp.raise_for_status()
                    await _check_discogs_rate_limit(search_resp)
                    results = search_resp.json().get("results", [])
                    if not results:
                        self.artist_repo.update_image(artist, image_path=None, status="not_found")
                        return None

                    discogs_id = results[0]["id"]

                    # Step 2: fetch artist detail to get primary image
                    detail_resp = await client.get(
                        f"https://api.discogs.com/artists/{discogs_id}",
                        headers=headers,
                        timeout=10.0,
                    )
                    detail_resp.raise_for_status()
                    await _check_discogs_rate_limit(detail_resp)
                    images = detail_resp.json().get("images", [])
                    primary = next(
                        (img for img in images if img.get("type") == "primary"),
                        images[0] if images else None,
                    )
                    if not primary:
                        self.artist_repo.update_image(artist, image_path=None, status="not_found")
                        return None

                    img_resp = await client.get(primary["uri"], timeout=15.0)
                    img_resp.raise_for_status()
                    image_path.write_bytes(img_resp.content)
                    self.artist_repo.update_image(artist, image_path=str(image_path), status="found")
                    return image_path

        except Exception as e:
            logger.warning("Failed to fetch artist image for %s: %s", name, e)
            return None


async def _check_discogs_rate_limit(response: httpx.Response) -> None:
    """Sleep if the Discogs rate-limit budget is nearly exhausted."""
    remaining_raw = response.headers.get("X-Discogs-Ratelimit-Remaining")
    if remaining_raw is None:
        return
    try:
        remaining = int(remaining_raw)
    except ValueError:
        return
    logger.debug("Discogs rate limit remaining: %s", remaining)
    if remaining <= _DISCOGS_RATE_LIMIT_LOW:
        logger.warning(
            "Discogs rate limit nearly exhausted (%s remaining), sleeping %.1fs",
            remaining,
            _DISCOGS_RATE_LIMIT_SLEEP,
        )
        await asyncio.sleep(_DISCOGS_RATE_LIMIT_SLEEP)
