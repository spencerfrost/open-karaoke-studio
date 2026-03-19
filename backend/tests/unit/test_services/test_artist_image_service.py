"""Unit tests for app/services/artist_image_service.py."""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.artist_image_service import ArtistImageService, _slugify


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
# ArtistImageService.get_or_fetch_artist_image
# ---------------------------------------------------------------------------


@pytest.fixture
def file_service():
    fs = MagicMock()
    # Default: paths don't exist
    fs.get_artist_image_path.return_value = MagicMock(spec=Path, exists=MagicMock(return_value=False))
    fs.get_artist_notfound_path.return_value = MagicMock(spec=Path, exists=MagicMock(return_value=False))
    return fs


@pytest.fixture
def svc(file_service):
    return ArtistImageService(file_service=file_service)


@pytest.mark.asyncio
async def test_returns_cached_image_if_exists(svc, file_service):
    cached_path = MagicMock(spec=Path)
    cached_path.exists.return_value = True
    file_service.get_artist_image_path.return_value = cached_path

    result = await svc.get_or_fetch_artist_image("Queen")

    assert result is cached_path


@pytest.mark.asyncio
async def test_returns_none_if_notfound_marker_exists(svc, file_service):
    image_path = MagicMock(spec=Path)
    image_path.exists.return_value = False
    notfound_path = MagicMock(spec=Path)
    notfound_path.exists.return_value = True

    file_service.get_artist_image_path.return_value = image_path
    file_service.get_artist_notfound_path.return_value = notfound_path

    result = await svc.get_or_fetch_artist_image("Unknown Artist")
    assert result is None


@pytest.mark.asyncio
async def test_fetches_and_saves_image_when_found(svc, file_service):
    image_path = MagicMock(spec=Path)
    image_path.exists.return_value = False
    image_path.parent = MagicMock()
    notfound_path = MagicMock(spec=Path)
    notfound_path.exists.return_value = False

    file_service.get_artist_image_path.return_value = image_path
    file_service.get_artist_notfound_path.return_value = notfound_path

    mock_img_resp = MagicMock()
    mock_img_resp.content = b"fake_image_bytes"

    mock_search_resp = MagicMock()
    mock_search_resp.json.return_value = {
        "artists": [{"strArtistThumb": "https://example.com/queen.jpg"}]
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=[mock_search_resp, mock_img_resp])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.artist_image_service.httpx.AsyncClient", return_value=mock_client):
        result = await svc.get_or_fetch_artist_image("Queen")

    assert result is image_path
    image_path.write_bytes.assert_called_once_with(b"fake_image_bytes")


@pytest.mark.asyncio
async def test_creates_notfound_marker_when_no_artists(svc, file_service):
    image_path = MagicMock(spec=Path)
    image_path.exists.return_value = False
    image_path.parent = MagicMock()
    notfound_path = MagicMock(spec=Path)
    notfound_path.exists.return_value = False

    file_service.get_artist_image_path.return_value = image_path
    file_service.get_artist_notfound_path.return_value = notfound_path

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"artists": None}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.artist_image_service.httpx.AsyncClient", return_value=mock_client):
        result = await svc.get_or_fetch_artist_image("NoArtist")

    assert result is None
    notfound_path.touch.assert_called_once()


@pytest.mark.asyncio
async def test_creates_notfound_marker_when_no_thumb_url(svc, file_service):
    image_path = MagicMock(spec=Path)
    image_path.exists.return_value = False
    image_path.parent = MagicMock()
    notfound_path = MagicMock(spec=Path)
    notfound_path.exists.return_value = False

    file_service.get_artist_image_path.return_value = image_path
    file_service.get_artist_notfound_path.return_value = notfound_path

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"artists": [{"strArtistThumb": None}]}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.artist_image_service.httpx.AsyncClient", return_value=mock_client):
        result = await svc.get_or_fetch_artist_image("NoThumb")

    assert result is None
    notfound_path.touch.assert_called_once()


@pytest.mark.asyncio
async def test_returns_none_on_network_error(svc, file_service):
    image_path = MagicMock(spec=Path)
    image_path.exists.return_value = False
    image_path.parent = MagicMock()
    notfound_path = MagicMock(spec=Path)
    notfound_path.exists.return_value = False

    file_service.get_artist_image_path.return_value = image_path
    file_service.get_artist_notfound_path.return_value = notfound_path

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("network error"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.artist_image_service.httpx.AsyncClient", return_value=mock_client):
        result = await svc.get_or_fetch_artist_image("ErrorArtist")

    assert result is None
