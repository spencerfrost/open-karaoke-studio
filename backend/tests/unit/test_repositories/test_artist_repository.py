"""Tests for app/repositories/artist_repository.py, on the shared test database."""

import pytest

from app.db.models import DbArtist, DbSong, DbSongArtist
from app.repositories.artist_repository import ArtistRepository


@pytest.fixture
def repo(test_db_session):
    return ArtistRepository(test_db_session)


def test_get_by_name_ignores_case_and_spaces(repo):
    queen = repo.get_or_create("Queen")

    assert repo.get_by_name("  QUEEN ") == queen
    assert repo.get_by_name("Unknown") is None


def test_get_or_create_stores_normalized_name_and_given_display_name(repo):
    artist = repo.get_or_create("  AC/DC ", display_name="AC/DC")

    assert artist.name == "ac/dc"
    assert artist.display_name == "AC/DC"


def test_get_or_create_returns_the_existing_artist(repo, test_db_session):
    first = repo.get_or_create("Queen")

    assert repo.get_or_create("queen") == first
    assert test_db_session.query(DbArtist).count() == 1


def test_get_or_create_upgrades_a_lowercase_display_name(repo):
    repo.get_or_create("björk", display_name="björk")

    artist = repo.get_or_create("Björk", display_name="Björk")

    assert artist.display_name == "Björk"


def test_get_or_create_keeps_a_hand_set_display_name(repo):
    artist = repo.get_or_create("prince")
    repo.update_display_name(artist, "Prince & The Revolution")

    artist = repo.get_or_create("Prince", display_name="Prince")

    assert artist.display_name == "Prince & The Revolution"


def test_get_all_with_image_status(repo):
    found = repo.get_or_create("Queen")
    repo.update_image(found, image_path="/library/artists/queen.jpg", status="found")
    repo.get_or_create("Nobody")

    assert repo.get_all_with_image_status("found") == [found]
    assert found.image_path == "/library/artists/queen.jpg"


def test_delete_removes_songs_credited_only_by_artist_id(repo, test_db_session):
    artist = repo.get_or_create("Queen")
    other = repo.get_or_create("David Bowie")
    test_db_session.add_all(
        [
            DbSong(id="legacy", title="Legacy", artist="Queen", artist_id=artist.id),
            DbSong(id="shared", title="Shared", artist="Queen", artist_id=artist.id),
            DbSongArtist(song_id="shared", artist_id=other.id, role="primary"),
        ]
    )
    test_db_session.commit()

    result = repo.delete_with_cascade(artist)

    assert result == {"deleted_songs": 1, "unlinked_songs": 0}
    assert test_db_session.get(DbSong, "legacy") is None
    assert test_db_session.get(DbSong, "shared") is not None
