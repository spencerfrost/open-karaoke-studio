"""Unit tests for app/repositories/album_repository.py."""
from unittest.mock import MagicMock, Mock

import pytest

from app.db.models.album import DbAlbum
from app.repositories.album_repository import AlbumRepository


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def repo(db):
    return AlbumRepository(db=db)


def test_get_by_itunes_id_returns_album(repo, db):
    mock_album = MagicMock(spec=DbAlbum)
    db.query.return_value.filter.return_value.first.return_value = mock_album

    result = repo.get_by_itunes_id(12345)

    assert result is mock_album


def test_get_by_itunes_id_returns_none_when_missing(repo, db):
    db.query.return_value.filter.return_value.first.return_value = None

    result = repo.get_by_itunes_id(99999)

    assert result is None


def test_get_or_create_returns_existing_album(repo, db):
    existing = MagicMock(spec=DbAlbum)
    db.query.return_value.filter.return_value.first.return_value = existing

    result = repo.get_or_create(title="Abbey Road", itunes_collection_id=111, artist_id=1)

    assert result is existing
    db.add.assert_not_called()


def test_get_or_create_creates_new_album(repo, db):
    db.query.return_value.filter.return_value.first.return_value = None

    result = repo.get_or_create(
        title="Abbey Road",
        itunes_collection_id=222,
        artist_id=5,
        release_date="1969-09-26",
    )

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


def test_update_cover_sets_path_and_status(repo, db):
    album = MagicMock(spec=DbAlbum)

    result = repo.update_cover(album, "covers/222.jpg")

    assert album.cover_path == "covers/222.jpg"
    assert album.image_status == "found"
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(album)
