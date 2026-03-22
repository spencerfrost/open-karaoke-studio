"""Unit tests for app/services/artist_image_service.py."""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.repositories.artist_repository import ArtistRepository
from app.services.artist_image_service import ArtistImageService, _slugify
from app.services.file_service import FileService


# ---------------------------------------------------------------------------
# _slugify helper
# ---------------------------------------------------------------------------


def test_slugify_basic():
    assert _slugify("Rick Astley") == "rick-astley"


def test_slugify_removes_special_chars():
    assert _slugify("AC/DC") == "acdc"


def test_slugify_handles_unicode():
    result = _slugify("Björk")
    assert " " not in result


def test_slugify_lowercases():
    assert _slugify("QUEEN") == "queen"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_artist():
    artist = MagicMock()
    artist.image_status = "not_checked"
    artist.image_path = None
    return artist


@pytest.fixture
def artist_repo(mock_artist):
    repo = Mock(spec=ArtistRepository)
    repo.get_or_create.return_value = mock_artist
    return repo


@pytest.fixture
def file_service():
    fs = Mock(spec=FileService)
    image_path = MagicMock(spec=Path)
    image_path.parent = MagicMock()
    fs.get_artist_image_path.return_value = image_path
    return fs


@pytest.fixture
def svc(file_service, artist_repo):
    return ArtistImageService(file_service=file_service, artist_repo=artist_repo)


# ---------------------------------------------------------------------------
# ArtistImageService.get_or_fetch_artist_image
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_returns_cached_image_if_exists(svc, artist_repo, mock_artist):
    mock_artist.image_status = "found"
    mock_artist.image_path = "/library/artists/queen.jpg"

    result = await svc.get_or_fetch_artist_image("Queen")

    assert result == Path("/library/artists/queen.jpg")
    artist_repo.update_image.assert_not_called()


@pytest.mark.asyncio
async def test_returns_none_if_notfound_marker_exists(svc, artist_repo, mock_artist):
    mock_artist.image_status = "not_found"

    result = await svc.get_or_fetch_artist_image("Unknown Artist")

    assert result is None
    artist_repo.update_image.assert_not_called()


@pytest.mark.asyncio
async def test_fetches_and_saves_image_when_found(svc, artist_repo, file_service, mock_artist):
    image_path = file_service.get_artist_image_path.return_value

    mock_search_resp = MagicMock()
    mock_search_resp.json.return_value = {
        "artists": [{"strArtistThumb": "https://example.com/queen.jpg"}]
    }
    mock_img_resp = MagicMock()
    mock_img_resp.content = b"fake_image_bytes"

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=[mock_search_resp, mock_img_resp])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.artist_image_service.httpx.AsyncClient", return_value=mock_client):
        result = await svc.get_or_fetch_artist_image("Queen")

    assert result is image_path
    image_path.write_bytes.assert_called_once_with(b"fake_image_bytes")
    artist_repo.update_image.assert_called_once_with(
        mock_artist, image_path=str(image_path), status="found"
    )


@pytest.mark.asyncio
async def test_creates_notfound_when_no_artists(svc, artist_repo, mock_artist):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"artists": None}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.artist_image_service.httpx.AsyncClient", return_value=mock_client):
        result = await svc.get_or_fetch_artist_image("NoArtist")

    assert result is None
    artist_repo.update_image.assert_called_once_with(
        mock_artist, image_path=None, status="not_found"
    )


@pytest.mark.asyncio
async def test_creates_notfound_when_no_thumb_url(svc, artist_repo, mock_artist):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"artists": [{"strArtistThumb": None}]}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.artist_image_service.httpx.AsyncClient", return_value=mock_client):
        result = await svc.get_or_fetch_artist_image("NoThumb")

    assert result is None
    artist_repo.update_image.assert_called_once_with(
        mock_artist, image_path=None, status="not_found"
    )


@pytest.mark.asyncio
async def test_returns_none_on_network_error(svc, artist_repo, mock_artist):
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("network error"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.artist_image_service.httpx.AsyncClient", return_value=mock_client):
        result = await svc.get_or_fetch_artist_image("ErrorArtist")

    assert result is None
    # Status stays "not_checked" — transient failures don't poison the cache
    artist_repo.update_image.assert_not_called()
