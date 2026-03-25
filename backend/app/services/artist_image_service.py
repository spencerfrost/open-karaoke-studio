import asyncio
import logging
import re
from collections.abc import Callable
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.config import get_config
from app.repositories.artist_repository import ArtistRepository

from .file_service import FileService

logger = logging.getLogger(__name__)

_DISCOGS_USER_AGENT = "OpenKaraokeStudio/1.0 +https://github.com/open-karaoke-studio"

# Discogs allows 60 req/min for authenticated requests (moving average window).
# We serialize all Discogs API calls behind a lock and sleep when the budget
# runs low.  The lock ensures the sleep actually blocks every caller — without
# it, concurrent coroutines keep firing requests during the "sleep" window.
_DISCOGS_LOCK = asyncio.Lock()
_DISCOGS_RATE_LIMIT_LOW = 5  # sleep when remaining budget falls to this value
_DISCOGS_RATE_LIMIT_SLEEP = 2.0  # seconds to sleep when budget is low


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-"))


class ArtistImageService:
    def __init__(
        self,
        file_service: FileService,
        session_factory: Callable[[], Session],
    ):
        self.file_service = file_service
        self._session_factory = session_factory

    def _repo(self) -> tuple[Session, ArtistRepository]:
        """Create a short-lived DB session + repo pair.  Caller must close."""
        db = self._session_factory()
        return db, ArtistRepository(db)

    async def get_or_fetch_artist_image(self, name: str) -> Path | None:
        # --- Phase 1: quick DB lookup (then release connection) ---
        db, repo = self._repo()
        try:
            artist = repo.get_or_create(name)
            if artist.image_status == "found" and artist.image_path:
                cached_path = Path(artist.image_path)
                if cached_path.exists():
                    return cached_path
                # Cached path may be stale (e.g. after project relocation).
                # Check if the image already exists at the current expected location.
                _slug = _slugify(name)
                current_path = self.file_service.get_artist_image_path(_slug)
                if current_path.exists():
                    return current_path
                # File is missing entirely — fall through to re-fetch from Discogs
            if artist.image_status == "not_found":
                return None
            artist_id = artist.id
        finally:
            db.close()

        # --- Phase 2: Discogs HTTP fetch (no DB connection held) ---
        slug = _slugify(name)
        image_path = self.file_service.get_artist_image_path(slug)
        image_path.parent.mkdir(parents=True, exist_ok=True)

        token = get_config().DISCOGS_TOKEN
        headers = {
            "Authorization": f"Discogs token={token}",
            "User-Agent": _DISCOGS_USER_AGENT,
        }

        fetched_path: Path | None = None
        status = "not_found"

        try:
            async with httpx.AsyncClient() as client:
                # Step 1: search for artist to get Discogs artist ID
                search_resp = await _discogs_get(
                    client,
                    "https://api.discogs.com/database/search",
                    params={"q": name, "type": "artist"},
                    headers=headers,
                    timeout=10.0,
                )
                search_resp.raise_for_status()
                results = search_resp.json().get("results", [])
                if not results:
                    fetched_path = None
                    status = "not_found"
                else:
                    discogs_id = results[0]["id"]

                    # Step 2: fetch artist detail to get primary image
                    detail_resp = await _discogs_get(
                        client,
                        f"https://api.discogs.com/artists/{discogs_id}",
                        headers=headers,
                        timeout=10.0,
                    )
                    detail_resp.raise_for_status()
                    images = detail_resp.json().get("images", [])
                    primary = next(
                        (img for img in images if img.get("type") == "primary"),
                        images[0] if images else None,
                    )
                    if not primary:
                        fetched_path = None
                        status = "not_found"
                    else:
                        # Image CDN downloads don't count against Discogs API rate limit
                        img_resp = await client.get(primary["uri"], timeout=15.0)
                        img_resp.raise_for_status()
                        image_path.write_bytes(img_resp.content)
                        fetched_path = image_path
                        status = "found"

        except Exception as e:
            logger.warning("Failed to fetch artist image for %s: %s", name, e)
            return None

        # --- Phase 3: persist result (short-lived DB session) ---
        db, repo = self._repo()
        try:
            artist = repo.get_by_id(artist_id)
            if artist is not None:
                repo.update_image(
                    artist,
                    image_path=str(fetched_path) if fetched_path else None,
                    status=status,
                )
        finally:
            db.close()

        return fetched_path


    async def search_artist_images(self, query: str) -> list[dict]:
        """Search Discogs for artist images and return multiple candidates.

        Uses a single search API call; no per-artist detail fetches.
        Filters out placeholder (spacer.gif) images.
        """
        token = get_config().DISCOGS_TOKEN
        headers = {
            "Authorization": f"Discogs token={token}",
            "User-Agent": _DISCOGS_USER_AGENT,
        }
        try:
            async with httpx.AsyncClient() as client:
                search_resp = await _discogs_get(
                    client,
                    "https://api.discogs.com/database/search",
                    params={"q": query, "type": "artist"},
                    headers=headers,
                    timeout=10.0,
                )
                search_resp.raise_for_status()
                results = search_resp.json().get("results", [])
        except Exception as e:
            logger.warning("Failed to search Discogs images for %r: %s", query, e)
            return []

        candidates = []
        for result in results[:10]:
            cover = result.get("cover_image", "")
            thumb = result.get("thumb", "")
            title = result.get("title", "")
            # Skip Discogs spacer placeholder images
            if cover and "spacer" not in cover:
                candidates.append({"thumb": thumb or cover, "uri": cover, "title": title})
            elif thumb and "spacer" not in thumb:
                candidates.append({"thumb": thumb, "uri": thumb, "title": title})
        return candidates

    async def set_image_from_url(self, artist_id: int, image_url: str) -> "Path | None":
        """Download an image from ``image_url`` and save it as this artist's image.

        CDN downloads do not count against the Discogs API rate limit, so no
        lock is needed here.
        """
        # Phase 1: resolve artist slug (short-lived DB session)
        db, repo = self._repo()
        try:
            artist = repo.get_by_id(artist_id)
            if artist is None:
                return None
            slug = _slugify(artist.name)
        finally:
            db.close()

        # Phase 2: download image directly from the CDN URL
        image_path = self.file_service.get_artist_image_path(slug)
        image_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(image_url, timeout=15.0)
                resp.raise_for_status()
                image_path.write_bytes(resp.content)
        except Exception as e:
            logger.warning("Failed to download artist image from %s: %s", image_url, e)
            return None

        # Phase 3: persist result
        db, repo = self._repo()
        try:
            artist = repo.get_by_id(artist_id)
            if artist is not None:
                repo.update_image(artist, image_path=str(image_path), status="found")
        finally:
            db.close()

        return image_path


async def _discogs_get(
    client: httpx.AsyncClient, url: str, **kwargs: object
) -> httpx.Response:
    """Make a serialised, rate-limited GET to the Discogs API.

    Holds ``_DISCOGS_LOCK`` for the entire request-then-maybe-sleep cycle so
    that no other coroutine can fire a request while we're waiting on a
    low rate-limit budget.
    """
    async with _DISCOGS_LOCK:
        response = await client.get(url, **kwargs)
        remaining_raw = response.headers.get("X-Discogs-Ratelimit-Remaining")
        if remaining_raw is not None:
            try:
                remaining = int(remaining_raw)
            except ValueError:
                remaining = None
            if remaining is not None:
                logger.debug("Discogs rate limit remaining: %s", remaining)
                if remaining <= _DISCOGS_RATE_LIMIT_LOW:
                    logger.warning(
                        "Discogs rate limit nearly exhausted (%s remaining), sleeping %.1fs",
                        remaining,
                        _DISCOGS_RATE_LIMIT_SLEEP,
                    )
                    await asyncio.sleep(_DISCOGS_RATE_LIMIT_SLEEP)
        return response
