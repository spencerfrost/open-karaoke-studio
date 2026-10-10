"""Tests for fetching a cover for albums that have an iTunes collection id but no cover."""

from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest
import requests
from tests.fastapi.conftest import _TestingSessionLocal

from app.db.models import DbAlbum
from app.services.itunes_service import fetch_album_cover


@contextmanager
def _test_db_session():
    session = _TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def use_test_db():
    with patch("app.db.database.get_db_session", _test_db_session):
        yield


@pytest.fixture
def album_id():
    with _test_db_session() as session:
        album = DbAlbum(title="Rumours", itunes_collection_id=1234)
        session.add(album)
        session.commit()
        yield album.id
        session.query(DbAlbum).delete()
        session.commit()


def _album(album_id):
    with _test_db_session() as session:
        album = session.get(DbAlbum, album_id)
        return album.image_status, album.cover_path


def _itunes_returns(results):
    response = Mock()
    response.json.return_value = {"results": results}
    return patch("app.services.itunes_service.requests.get", return_value=response)


def test_downloads_the_cover(album_id):
    with (
        _itunes_returns([{"artworkUrl100": "https://x/100x100bb.jpg"}]),
        patch(
            "app.services.itunes_service._download_itunes_cover",
            return_value="covers/1234.jpg",
        ) as download,
    ):
        assert fetch_album_cover(album_id) == "found"

    download.assert_called_once_with(1234, "https://x/100x100bb.jpg")
    assert _album(album_id) == ("found", "covers/1234.jpg")


def test_no_artwork_marks_the_album_so_it_is_not_asked_again(album_id):
    with _itunes_returns([]):
        assert fetch_album_cover(album_id) == "not_found"

    assert _album(album_id) == ("not_found", None)


def test_a_network_error_leaves_the_album_for_the_next_run(album_id):
    with patch(
        "app.services.itunes_service.requests.get",
        side_effect=requests.ConnectionError("offline"),
    ):
        assert fetch_album_cover(album_id) == "error"

    assert _album(album_id) == ("not_checked", None)


def test_a_failed_download_leaves_the_album_for_the_next_run(album_id):
    with (
        _itunes_returns([{"artworkUrl100": "https://x/100x100bb.jpg"}]),
        patch("app.services.itunes_service._download_itunes_cover", return_value=None),
    ):
        assert fetch_album_cover(album_id) == "error"

    assert _album(album_id) == ("not_checked", None)
