"""Tests for app/repositories/artist_repository.py, on the shared test database."""

import pytest

from app.db.models import DbArtist, DbSong, DbSongArtist
from app.repositories.artist_repository import ArtistRepository


@pytest.fixture
def repo(test_db_session):
    return ArtistRepository(test_db_session)


def test_get_by_name_ignores_case_and_spaces(repo):
    queen = repo.resolve("Queen")

    assert repo.get_by_name("  QUEEN ") == queen
    assert repo.get_by_name("Unknown") is None


def test_resolve_stores_normalized_name_and_cased_display_name(repo):
    artist = repo.resolve("  AC/DC ")

    assert artist.name == "ac/dc"
    assert artist.display_name == "AC/DC"


def test_resolve_returns_the_existing_artist(repo, test_db_session):
    first = repo.resolve("Queen")

    assert repo.resolve("queen") == first
    assert test_db_session.query(DbArtist).count() == 1


def test_resolve_upgrades_a_lowercase_display_name(repo):
    repo.resolve("björk")

    artist = repo.resolve("Björk")

    assert artist.display_name == "Björk"


def test_resolve_keeps_a_hand_set_display_name(repo):
    artist = repo.resolve("prince")
    repo.update_display_name(artist, "Prince & The Revolution")

    artist = repo.resolve("Prince")

    assert artist.display_name == "Prince & The Revolution"


def test_get_all_with_image_status(repo):
    found = repo.resolve("Queen")
    repo.update_image(found, image_path="/library/artists/queen.jpg", status="found")
    repo.resolve("Nobody")

    assert repo.get_all_with_image_status("found") == [found]
    assert found.image_path == "/library/artists/queen.jpg"


def test_delete_if_unused(repo, test_db_session):
    used = repo.resolve("Queen")
    unused = repo.resolve("Nobody")
    test_db_session.add(DbSong(id="s", title="S", artist="Queen", artist_id=used.id))
    test_db_session.commit()

    assert repo.delete_if_unused(used) is False
    assert repo.delete_if_unused(unused) is True
    assert test_db_session.query(DbArtist).all() == [used]


def test_delete_removes_songs_credited_only_by_artist_id(repo, test_db_session):
    artist = repo.resolve("Queen")
    other = repo.resolve("David Bowie")
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
