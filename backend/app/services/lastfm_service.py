import logging
import re

import httpx

from app.config import get_config
from app.repositories.artist_repository import ArtistRepository

logger = logging.getLogger(__name__)

# Last.fm appends a "Read more on Last.fm" link as HTML — strip it
_LASTFM_SUFFIX_RE = re.compile(r'\s*<a href="https://www\.last\.fm[^"]*"[^>]*>.*?</a>\s*$', re.IGNORECASE | re.DOTALL)


def _clean_bio(content: str) -> str:
    """Strip the trailing 'Read more on Last.fm' anchor that Last.fm appends to bios."""
    return _LASTFM_SUFFIX_RE.sub("", content).strip()


class LastFmService:
    def __init__(self, artist_repo: ArtistRepository):
        self.artist_repo = artist_repo

    async def get_or_fetch_artist_bio(self, name: str) -> str | None:
        artist = self.artist_repo.get_or_create(name)

        if artist.bio_status == "found":
            return artist.bio
        if artist.bio_status == "not_found":
            return None

        # "not_checked" — fetch from Last.fm
        api_key = get_config().LASTFM_API_KEY
        if not api_key:
            logger.warning("LASTFM_API_KEY not configured; skipping bio fetch for %s", name)
            return None

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "http://ws.audioscrobbler.com/2.0/",
                    params={
                        "method": "artist.getinfo",
                        "artist": name,
                        "api_key": api_key,
                        "format": "json",
                    },
                    timeout=10.0,
                )
                resp.raise_for_status()
                data = resp.json()

                # Last.fm returns {"error": 6, "message": "Artist not found"} for unknown artists
                if "error" in data:
                    self.artist_repo.update_bio(artist, bio=None, status="not_found")
                    return None

                bio_content = data.get("artist", {}).get("bio", {}).get("content", "")
                bio = _clean_bio(bio_content) if bio_content else None

                if bio:
                    self.artist_repo.update_bio(artist, bio=bio, status="found")
                    return bio
                else:
                    self.artist_repo.update_bio(artist, bio=None, status="not_found")
                    return None

        except Exception:
            logger.warning("Failed to fetch Last.fm bio for %s", name, exc_info=True)
            return None
