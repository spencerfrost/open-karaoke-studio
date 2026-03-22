"""Unit tests for app/services/lastfm_service.py."""
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.repositories.artist_repository import ArtistRepository
from app.services.lastfm_service import LastFmService, _clean_bio


# ---------------------------------------------------------------------------
# _clean_bio helper
# ---------------------------------------------------------------------------

def test_clean_bio_strips_lastfm_link():
    raw = 'Queen are a British rock band. <a href="https://www.last.fm/music/Queen">Read more on Last.fm</a>'
    result = _clean_bio(raw)
    assert "Read more on Last.fm" not in result
    assert "Queen are a British rock band." in result


def test_clean_bio_leaves_plain_text_unchanged():
    plain = "Just a plain biography."
    assert _clean_bio(plain) == plain


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_artist():
    artist = MagicMock()
    artist.bio_status = "not_checked"
    artist.bio = None
    return artist


@pytest.fixture
def artist_repo(mock_artist):
    repo = Mock(spec=ArtistRepository)
    repo.get_or_create.return_value = mock_artist
    return repo


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.LASTFM_API_KEY = "test-lastfm-key"
    return cfg


@pytest.fixture
def svc(artist_repo):
    return LastFmService(artist_repo=artist_repo)


# ---------------------------------------------------------------------------
# Cache hits
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_returns_cached_bio(svc, artist_repo, mock_artist):
    mock_artist.bio_status = "found"
    mock_artist.bio = "Cached bio text."

    result = await svc.get_or_fetch_artist_bio("Queen")

    assert result == "Cached bio text."
    artist_repo.update_bio.assert_not_called()


@pytest.mark.asyncio
async def test_returns_none_for_notfound_marker(svc, artist_repo, mock_artist):
    mock_artist.bio_status = "not_found"

    result = await svc.get_or_fetch_artist_bio("Unknown Artist")

    assert result is None
    artist_repo.update_bio.assert_not_called()


# ---------------------------------------------------------------------------
# API fetches
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetches_and_caches_bio(svc, artist_repo, mock_artist, mock_config):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "artist": {"bio": {"content": "Great band. Formed in 1970."}}
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.lastfm_service.httpx.AsyncClient", return_value=mock_client), \
         patch("app.services.lastfm_service.get_config", return_value=mock_config):
        result = await svc.get_or_fetch_artist_bio("Queen")

    assert result == "Great band. Formed in 1970."
    artist_repo.update_bio.assert_called_once_with(
        mock_artist, bio="Great band. Formed in 1970.", status="found"
    )


@pytest.mark.asyncio
async def test_marks_notfound_when_api_returns_error(svc, artist_repo, mock_artist, mock_config):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"error": 6, "message": "Artist not found"}
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.lastfm_service.httpx.AsyncClient", return_value=mock_client), \
         patch("app.services.lastfm_service.get_config", return_value=mock_config):
        result = await svc.get_or_fetch_artist_bio("NoSuchArtist")

    assert result is None
    artist_repo.update_bio.assert_called_once_with(mock_artist, bio=None, status="not_found")


@pytest.mark.asyncio
async def test_marks_notfound_when_empty_bio(svc, artist_repo, mock_artist, mock_config):
    """API returns success but bio content is empty string → not_found."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "artist": {"bio": {"content": ""}}
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.lastfm_service.httpx.AsyncClient", return_value=mock_client), \
         patch("app.services.lastfm_service.get_config", return_value=mock_config):
        result = await svc.get_or_fetch_artist_bio("EmptyBioArtist")

    assert result is None
    artist_repo.update_bio.assert_called_once_with(mock_artist, bio=None, status="not_found")


@pytest.mark.asyncio
async def test_returns_none_on_network_error(svc, artist_repo, mock_artist, mock_config):
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.lastfm_service.httpx.AsyncClient", return_value=mock_client), \
         patch("app.services.lastfm_service.get_config", return_value=mock_config):
        result = await svc.get_or_fetch_artist_bio("Queen")

    assert result is None
    artist_repo.update_bio.assert_not_called()


@pytest.mark.asyncio
async def test_returns_none_when_no_api_key(svc, artist_repo, mock_artist):
    cfg = MagicMock()
    cfg.LASTFM_API_KEY = ""
    with patch("app.services.lastfm_service.get_config", return_value=cfg):
        result = await svc.get_or_fetch_artist_bio("Queen")
    assert result is None
    artist_repo.update_bio.assert_not_called()
