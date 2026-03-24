# backend/app/services/itunes_service.py
import logging
import time
from datetime import datetime
from typing import Any

import requests

logger = logging.getLogger(__name__)


def search_itunes(
    artist: str, title: str, album: str = "", limit: int = 5
) -> list[dict[str, Any]]:
    """
    Search iTunes for song metadata with sorting by release date.

    Args:
        artist (str): Artist name
        title (str): Song title
        album (str): Album name (optional, used to improve search)
        limit (int): Maximum number of results to return

    Returns:
        List[Dict[str, Any]]: List of song metadata sorted by release date (new first)
    """
    try:
        # Build search term - iTunes works best with simple search terms
        search_terms = []
        if artist:
            search_terms.append(artist)
        if title:
            search_terms.append(title)
        if album:
            search_terms.append(album)

        search_query = " ".join(search_terms)
        # iTunes Search API parameters
        params = {
            "term": search_query,
            "entity": "song",  # Search for songs specifically
            "media": "music",
            "limit": min(50, limit * 5),  # Get more results to filter through
            "sort": "recent",  # Sort by release date (newest first)
            "country": "US",  # Can be made configurable
        }

        logger.info(
            "Searching iTunes with query: '%s' (limit: %s)",
            search_query,
            params["limit"],
        )

        # Log the full request details
        url = "https://itunes.apple.com/search"
        headers = {"User-Agent": "curl/8.0.0", "Accept": "*/*"}

        logging.debug("iTunes API Request Details:")
        logging.debug("  URL: %s", url)
        logging.debug("  Params: %s", params)
        logging.debug("  Headers: %s", headers)

        # Make API request with one retry on 429 (rate limit)
        for _attempt in range(2):
            response = requests.get(url, params=params, timeout=10, headers=headers)

            # Log response details before checking status
            logging.debug("iTunes API Response Details:")
            logging.debug("  Status Code: %s", response.status_code)
            logging.debug("  Headers: %s", dict(response.headers))
            logging.debug("  URL Used: %s", response.url)

            if response.status_code == 429 and _attempt == 0:
                retry_after = int(response.headers.get("Retry-After", 30))
                logger.warning(
                    "iTunes rate limited (429). Sleeping %d s before retry…",
                    retry_after + 2,
                )
                time.sleep(retry_after + 2)
                continue
            break

        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        logger.info("iTunes returned %s raw results", len(results))

        matches = []
        for i, track in enumerate(results):
            try:
                # Extract metadata from iTunes response
                track_data = {
                    "id": track.get("trackId"),
                    "title": track.get("trackName"),
                    "artist": track.get("artistName"),
                    "artistId": track.get("artistId"),
                    "album": track.get("collectionName"),
                    "albumId": track.get("collectionId"),
                    "releaseDate": track.get("releaseDate"),
                    "trackNumber": track.get("trackNumber"),
                    "discNumber": track.get("discNumber"),
                    "country": track.get("country"),
                    "price": track.get("trackPrice"),
                    "previewUrl": track.get("previewUrl"),
                    "collectionPrice": track.get("collectionPrice"),
                    "trackExplicitness": track.get("trackExplicitness"),
                    "collectionExplicitness": track.get("collectionExplicitness"),
                    "isStreamable": track.get("isStreamable", False),
                    # Artwork URLs - Phase 1 fix
                    "artworkUrl30": track.get("artworkUrl30"),
                    "artworkUrl60": track.get("artworkUrl60"),
                    "artworkUrl100": track.get("artworkUrl100"),
                }

                # Convert release date to a more readable format
                if track_data["releaseDate"]:
                    try:
                        release_dt = datetime.fromisoformat(
                            track_data["releaseDate"].replace("Z", "+00:00")
                        )
                        track_data["releaseYear"] = release_dt.year
                        track_data["releaseDateFormatted"] = release_dt.strftime(
                            "%Y-%m-%d"
                        )
                    except (ValueError, AttributeError):
                        track_data["releaseYear"] = None
                        track_data["releaseDateFormatted"] = None

                logging.debug(
                    "iTunes result %s: '%s' by %s (%s)",
                    i + 1,
                    track_data["title"],
                    track_data["artist"],
                    track_data.get("releaseDateFormatted", "Unknown date"),
                )

                matches.append(track_data)

            except Exception as e:
                logger.warning("Error processing iTunes track result: %s", e)
                continue

        # Apply additional filtering to prioritize canonical releases
        filtered_matches = _filter_canonical_releases(matches, artist, title)

        # Return only the requested number of results
        return filtered_matches[:limit]

    except requests.RequestException as e:
        logger.error("iTunes API request error for query '%s': %s", search_query, e)

        # Log detailed error information
        if hasattr(e, "response") and e.response is not None:
            response = e.response
            logger.error("iTunes API Error Details:")
            logger.error("  Status Code: %s", response.status_code)
            logger.error("  Reason: %s", response.reason)
            logger.error("  URL: %s", response.url)
            logger.error("  Response Headers: %s", dict(response.headers))

            # Try to get response content for more details
            try:
                content = response.text[:1000]  # First 1000 chars to avoid huge logs
                if content:
                    logger.error("  Response Body (first 1000 chars): %s", content)
            except Exception:
                logger.error("  Could not read response body")

            # Log specific error analysis for common HTTP status codes
            if response.status_code == 403:
                logger.error("  403 Forbidden Error Analysis:")
                logger.error("  - This may indicate rate limiting by Apple")
                logger.error("  - Your IP might be temporarily blocked")
                logger.error("  - Apple may have changed their API access policies")
                logger.error(
                    "  - Consider adding delays between requests or changing User-Agent"
                )
            elif response.status_code == 429:
                logger.error("  429 Too Many Requests - Rate limit exceeded")
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    logger.error("  Retry after: %s seconds", retry_after)
            elif response.status_code >= 500:
                logger.error("  Server error on Apple's side - may be temporary")
        else:
            logger.error("  Network error (no response): %s", type(e).__name__)

    except Exception as e:
        logger.error("iTunes search error for query '%s': %s", search_query, e)
        logger.error("  Error type: %s", type(e).__name__)
        import traceback

        logger.error("  Stack trace: %s", traceback.format_exc())

    return []


def lookup_itunes(track_id: int) -> dict[str, Any] | None:
    """
    Lookup comprehensive metadata for a specific iTunes track.
    
    This provides much richer metadata than search, including:
    - All artwork URLs (30, 60, 100px)
    - Complete genre information (primary genre name + ID)
    - Full collection/album details
    - Track/disc counts
    - Content advisory ratings
    - Copyright information
    
    Args:
        track_id (int): iTunes track ID from search results
        
    Returns:
        Dict[str, Any]: Comprehensive track metadata, or None if not found/error
    """
    try:
        url = "https://itunes.apple.com/lookup"
        params = {
            "id": track_id,
            "entity": "song",
        }
        
        logger.info("Looking up iTunes track ID: %s", track_id)
        
        headers = {"User-Agent": "curl/8.0.0", "Accept": "*/*"}
        
        logging.debug("iTunes Lookup API Request Details:")
        logging.debug("  URL: %s", url)
        logging.debug("  Params: %s", params)
        logging.debug("  Headers: %s", headers)
        
        response = requests.get(url, params=params, timeout=10, headers=headers)
        
        logging.debug("iTunes Lookup API Response Details:")
        logging.debug("  Status Code: %s", response.status_code)
        logging.debug("  Headers: %s", dict(response.headers))
        logging.debug("  URL Used: %s", response.url)
        
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            logger.warning("No results found for iTunes track ID: %s", track_id)
            return None
            
        # iTunes lookup returns the track as the first result
        track = results[0]
        
        logger.info("iTunes lookup successful for track ID %s: '%s' by %s", 
                   track_id, track.get("trackName"), track.get("artistName"))
        
        # Extract comprehensive metadata
        track_data = {
            "id": track.get("trackId"),
            "title": track.get("trackName"),
            "artist": track.get("artistName"),
            "artistId": track.get("artistId"),
            "album": track.get("collectionName"),
            "albumId": track.get("collectionId"),
            "releaseDate": track.get("releaseDate"),
            
            # Genre information (potentially includes subgenres)
            "genre": track.get("primaryGenreName"),
            "primaryGenreId": track.get("primaryGenreId"),
            "genreIds": track.get("genreIds", []),  # Array of genre IDs
            
            # Track details
            "trackNumber": track.get("trackNumber"),
            "trackCount": track.get("trackCount"),
            "discNumber": track.get("discNumber"),
            "discCount": track.get("discCount"),
            "trackTimeMillis": track.get("trackTimeMillis"),
            
            # Artwork URLs - all sizes
            "artworkUrl30": track.get("artworkUrl30"),
            "artworkUrl60": track.get("artworkUrl60"),
            "artworkUrl100": track.get("artworkUrl100"),
            # Note: 600px version typically needs URL manipulation
            
            # Content and pricing
            "previewUrl": track.get("previewUrl"),
            "trackExplicitness": track.get("trackExplicitness"),
            "collectionExplicitness": track.get("collectionExplicitness"),
            "contentAdvisoryRating": track.get("contentAdvisoryRating"),
            "trackPrice": track.get("trackPrice"),
            "collectionPrice": track.get("collectionPrice"),
            "trackRentalPrice": track.get("trackRentalPrice"),
            "collectionHdPrice": track.get("collectionHdPrice"),
            "currency": track.get("currency"),
            "country": track.get("country"),
            
            # Additional metadata
            "isStreamable": track.get("isStreamable", False),
            "copyright": track.get("copyright"),
            "description": track.get("longDescription") or track.get("shortDescription"),
            
            # Collection/Album details
            "collectionCensoredName": track.get("collectionCensoredName"),
            "trackCensoredName": track.get("trackCensoredName"),
            "artistViewUrl": track.get("artistViewUrl"),
            "collectionViewUrl": track.get("collectionViewUrl"),
            "trackViewUrl": track.get("trackViewUrl"),
            
            # Store the complete raw response for debugging/future use
            "rawData": track,
        }
        
        # Convert release date to a more readable format
        if track_data["releaseDate"]:
            try:
                release_dt = datetime.fromisoformat(
                    track_data["releaseDate"].replace("Z", "+00:00")
                )
                track_data["releaseYear"] = release_dt.year
                track_data["releaseDateFormatted"] = release_dt.strftime("%Y-%m-%d")
            except (ValueError, AttributeError):
                track_data["releaseYear"] = None
                track_data["releaseDateFormatted"] = None
        
        # Generate 600px artwork URL from 100px version (iTunes URL pattern)
        if track_data["artworkUrl100"]:
            track_data["artworkUrl600"] = track_data["artworkUrl100"].replace(
                "100x100", "600x600"
            )
        
        return track_data
        
    except requests.RequestException as e:
        logger.error("iTunes lookup API request error for track ID %s: %s", track_id, e)
        
        if hasattr(e, "response") and e.response is not None:
            response = e.response
            logger.error("iTunes Lookup API Error Details:")
            logger.error("  Status Code: %s", response.status_code)
            logger.error("  Reason: %s", response.reason)
            logger.error("  URL: %s", response.url)
            
            try:
                content = response.text[:1000]
                if content:
                    logger.error("  Response Body (first 1000 chars): %s", content)
            except Exception:
                logger.error("  Could not read response body")
        else:
            logger.error("  Network error (no response): %s", type(e).__name__)
            
        return None
        
    except Exception as e:
        logger.error("iTunes lookup error for track ID %s: %s", track_id, e)
        logger.error("  Error type: %s", type(e).__name__)
        import traceback
        logger.error("  Stack trace: %s", traceback.format_exc())
        return None


def _filter_canonical_releases(
    tracks: list[dict[str, Any]], artist_query: str, title_query: str
) -> list[dict[str, Any]]:
    """
    Filter and rank tracks to prioritize canonical releases.
    iTunes already sorts by release date, but we can do additional filtering.

    Args:
        tracks: List of iTunes track data
        artist_query: Original artist search query
        title_query: Original title search query

    Returns:
        List[Dict[str, Any]]: Filtered and ranked tracks
    """
    if not tracks:
        return tracks

    # Score each track for canonical likelihood
    scored_tracks = []

    for track in tracks:
        score = 0.0

        title = track.get("title", "").lower()
        artist = track.get("artist", "").lower()
        album = track.get("album", "").lower()

        # Exact matches get high scores
        if title == title_query.lower():
            score += 50
        elif title_query.lower() in title:
            score += 25

        if artist == artist_query.lower():
            score += 30
        elif artist_query.lower() in artist:
            score += 15

        # Avoid obvious compilation indicators
        compilation_keywords = [
            "greatest hits",
            "best of",
            "compilation",
            "collection",
            "anthology",
            "live",
            "karaoke",
            "tribute",
            "cover",
        ]

        if not any(keyword in album for keyword in compilation_keywords):
            score += 20

        # Prefer tracks that are streamable
        if track.get("isStreamable"):
            score += 10

        # Prefer non-explicit versions for karaoke (optional)
        if track.get("trackExplicitness") == "notExplicit":
            score += 5

        scored_tracks.append({"track": track, "score": score})

    # Sort by score (highest first), keeping iTunes' date sorting as secondary
    scored_tracks.sort(key=lambda x: x["score"], reverse=True)

    # Log the ranking
    logger.info("iTunes canonical ranking:")
    for i, item in enumerate(scored_tracks[:5]):  # Show top 5
        track = item["track"]
        logger.info(
            "%s. '%s' by %s [%s] - Score: %.1f",
            i + 1,
            track.get("title", "Unknown"),
            track.get("artist", "Unknown"),
            track.get("album", "Unknown"),
            item["score"],
        )

    return [item["track"] for item in scored_tracks]


def fetch_and_assign_album_art(song_id: str, title: str, artist: str) -> bool:
    """
    Search iTunes for a song, then download and assign the album cover if found.

    Creates the Album record, sets song.album_id, and downloads the cover image.
    Returns True if album art was successfully assigned, False otherwise.
    """
    from app.db.database import get_db_session
    from app.repositories.album_repository import AlbumRepository
    from app.repositories.artist_repository import ArtistRepository
    from app.repositories.song_repository import SongRepository

    results = search_itunes(artist=artist, title=title, limit=1)
    if not results:
        logger.info("iTunes: no results for '%s' by '%s'", title, artist)
        return False

    track = results[0]
    collection_id = track.get("albumId")
    album_title = track.get("album") or "Unknown Album"
    artwork_url = track.get("artworkUrl100")

    if not collection_id or not artwork_url:
        logger.info("iTunes: missing collection_id or artwork for '%s' by '%s'", title, artist)
        return False

    # Download the cover image
    cover_path = _download_itunes_cover(collection_id, artwork_url)
    if not cover_path:
        return False

    # Persist album record and link to song
    try:
        with get_db_session() as session:
            artist_repo = ArtistRepository(session)
            album_repo = AlbumRepository(session)
            song_repo = SongRepository(session)

            artist_rec = artist_repo.get_or_create(artist)
            album = album_repo.get_or_create(
                title=album_title,
                itunes_collection_id=collection_id,
                artist_id=artist_rec.id,
                release_date=track.get("releaseDateFormatted"),
            )
            if not album.cover_path:
                album_repo.update_cover(album, cover_path)

            song_repo.update(song_id, album_id=album.id, artist_id=artist_rec.id)

        logger.info(
            "Album art assigned for song %s: '%s' (collection %s)", song_id, album_title, collection_id
        )
        return True
    except Exception as e:
        logger.warning("Failed to persist album art for song %s: %s", song_id, e)
        return False


def _download_itunes_cover(collection_id: int, artwork_url_100: str) -> str | None:
    """Download iTunes artwork at 600px and cache locally. Returns relative path or None."""
    from app.config import get_config

    config = get_config()
    covers_dir = config.library_path / "covers"
    covers_dir.mkdir(exist_ok=True)
    dest = covers_dir / f"{collection_id}.jpg"

    if dest.exists():
        return f"covers/{collection_id}.jpg"

    url_600 = artwork_url_100.replace("100x100bb", "600x600bb").replace("100x100", "600x600")

    try:
        response = requests.get(url_600, timeout=10, headers={"User-Agent": "curl/8.0.0"})
        response.raise_for_status()
        dest.write_bytes(response.content)
        logger.info("Downloaded iTunes cover for collection %s", collection_id)
        return f"covers/{collection_id}.jpg"
    except Exception as e:
        logger.warning("Failed to download iTunes cover for collection %s: %s", collection_id, e)
        return None
