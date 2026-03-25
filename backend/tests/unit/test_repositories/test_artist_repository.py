"""Unit tests for app/repositories/artist_repository.py."""
from unittest.mock import MagicMock

import pytest

from app.db.models.artist import DbArtist
from app.repositories.artist_repository import ArtistRepository


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def repo(db):
    return ArtistRepository(db=db)


def test_get_by_name_returns_artist(repo, db):
    mock_artist = MagicMock(spec=DbArtist)
    db.query.return_value.filter.return_value.first.return_value = mock_artist

    result = repo.get_by_name("queen")

    assert result is mock_artist


def test_get_by_name_returns_none_when_missing(repo, db):
    db.query.return_value.filter.return_value.first.return_value = None

    result = repo.get_by_name("unknown")

    assert result is None


def test_get_or_create_returns_existing(repo, db):
    existing = MagicMock(spec=DbArtist)
    db.query.return_value.filter.return_value.first.return_value = existing

    result = repo.get_or_create("Queen")

    assert result is existing
    db.add.assert_not_called()


def test_get_or_create_creates_new(repo, db):
    db.query.return_value.filter.return_value.first.return_value = None

    result = repo.get_or_create("New Artist")

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


def test_update_image_sets_path_and_status(repo, db):
    artist = MagicMock(spec=DbArtist)

    repo.update_image(artist, image_path="/path/to/img.jpg", status="found")

    assert artist.image_path == "/path/to/img.jpg"
    assert artist.image_status == "found"
    db.commit.assert_called_once()
