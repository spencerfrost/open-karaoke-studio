"""Unit tests for app/repositories/album_repository.py."""

import pytest

from app.db.database import SessionLocal
from app.db.models import DbAlbum, DbSong
from app.repositories.album_repository import AlbumRepository


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.rollback()
    session.query(DbSong).filter(DbSong.id.like("album-repo-%")).delete(
        synchronize_session=False
    )
    session.query(DbAlbum).delete()
    session.commit()
    session.close()


@pytest.fixture
def repo(db):
    return AlbumRepository(db)


def test_get_or_create_returns_the_album_with_that_source_and_id(repo):
    first = repo.get_or_create(
        source="ytmusic", source_id="MPREb_1", title="Toys In The Attic"
    )
    again = repo.get_or_create(source="ytmusic", source_id="MPREb_1", title="Other")

    assert again.id == first.id
    assert again.title == "Toys In The Attic"


def test_the_same_id_from_another_source_is_another_album(repo):
    ytmusic = repo.get_or_create(source="ytmusic", source_id="123", title="A")
    deezer = repo.get_or_create(source="deezer", source_id="123", title="A")

    assert ytmusic.id != deezer.id


def test_get_or_create_survives_losing_the_race_to_create_it(repo, db):
    # Another worker inserts the album between the lookup and the insert.
    other = SessionLocal()
    other.add(DbAlbum(source="deezer", source_id="42", title="Rumours"))
    other.commit()
    other.close()
    real_get = repo.get_by_source
    calls = []

    def get_by_source(source, source_id):
        calls.append(source_id)
        return None if len(calls) == 1 else real_get(source, source_id)

    repo.get_by_source = get_by_source
    album = repo.get_or_create(source="deezer", source_id="42", title="Rumours")

    assert album.title == "Rumours"
    assert db.query(DbAlbum).filter(DbAlbum.source_id == "42").count() == 1


def test_update_cover_sets_path_and_status(repo):
    album = repo.get_or_create(source="deezer", source_id="7", title="Rumours")

    repo.update_cover(album, "covers/album-7.jpg")

    assert album.cover_path == "covers/album-7.jpg"
    assert album.image_status == "found"


def test_unlinked_lists_only_albums_no_song_links_to(repo, db):
    linked = repo.get_or_create(source="deezer", source_id="1", title="Linked")
    unlinked = repo.get_or_create(source="deezer", source_id="2", title="Unlinked")
    db.add(DbSong(id="album-repo-song", title="T", artist="A", album_id=linked.id))
    db.commit()

    assert [album.id for album in repo.unlinked()] == [unlinked.id]
