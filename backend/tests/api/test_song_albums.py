"""Tests for saving a song's album: the lookup's writes, hand-set albums and cleanup."""

from unittest.mock import Mock, patch

import pytest

from app.config import get_config
from app.db.database import get_db_session
from app.db.models import DbAlbum, DbSong
from app.jobs.batch_tasks import batch_fetch_albums
from app.services import album_service
from app.services.album_service import (
    AlbumLookupError,
    AlbumMatch,
    delete_unlinked_albums,
    refresh_song_album,
)
from app.utils.clock import utc_now

MATCH = AlbumMatch(
    source="ytmusic",
    source_id="MPREb_1",
    title="Toys In The Attic",
    year="1975",
    cover_url="https://yt3.googleusercontent.com/abc=w1200-h1200-s-l90-rj",
    explicit=False,
)


@pytest.fixture
def covers_dir():
    path = get_config().library_path / "covers"
    yield path
    for cover in path.glob("album-*"):
        cover.unlink()


def _add_song(db, song_id="s1", **fields):
    fields.setdefault("title", "Sweet Emotion")
    fields.setdefault("artist", "Aerosmith")
    db.add(DbSong(id=song_id, video_id="vid1", **fields))
    db.commit()


def _song(song_id="s1"):
    with get_db_session() as session:
        song = session.get(DbSong, song_id)
        session.expunge(song)
        return song


def _image(content=b"jpeg"):
    response = Mock(content=content, headers={"content-type": "image/jpeg"})
    response.raise_for_status.return_value = None
    return patch.object(album_service.requests, "get", return_value=response)


def _finds(match):
    return patch.object(album_service, "find_album", return_value=match)


class TestRefreshSongAlbum:
    def test_writes_the_name_link_cover_and_explicit_flag_together(
        self, db, covers_dir
    ):
        _add_song(db, album="Pandora's Box", explicit=None)

        with _finds(MATCH), _image(b"cover-bytes"):
            assert refresh_song_album("s1") == "found"

        song = _song()
        album = db.get(DbAlbum, song.album_id)
        assert song.album == "Toys In The Attic"
        assert song.explicit is False
        assert song.album_checked_at is None
        assert (album.source, album.source_id) == ("ytmusic", "MPREb_1")
        assert album.release_date == "1975"
        assert album.cover_path == f"covers/album-{album.id}.jpg"
        assert (covers_dir / f"album-{album.id}.jpg").read_bytes() == b"cover-bytes"

    def test_songs_on_the_same_album_share_it_and_its_cover(self, db, covers_dir):
        _add_song(db, "s1")
        _add_song(db, "s2", title="Walk This Way")

        with _finds(MATCH), _image() as get:
            refresh_song_album("s1")
            refresh_song_album("s2")

        assert _song("s1").album_id == _song("s2").album_id
        assert get.call_count == 1  # the second song reuses the cover

    def test_an_unknown_explicit_flag_leaves_the_songs_alone(self, db, covers_dir):
        _add_song(db, explicit=True)
        unknown = AlbumMatch(**{**MATCH.__dict__, "explicit": None})

        with _finds(unknown), _image():
            refresh_song_album("s1")

        assert _song().explicit is True

    def test_a_hand_set_album_is_never_looked_up(self, db):
        _add_song(db, album="Toys (Deluxe)", album_hand_set_at=utc_now())

        with _finds(MATCH) as find:
            assert refresh_song_album("s1") == "hand_set"

        find.assert_not_called()
        assert _song().album == "Toys (Deluxe)"

    def test_nothing_found_marks_the_song_checked(self, db):
        _add_song(db)

        with _finds(None):
            assert refresh_song_album("s1") == "not_found"

        assert _song().album_checked_at is not None

    def test_an_album_without_art_marks_the_song_checked(self, db):
        _add_song(db)
        no_art = AlbumMatch(**{**MATCH.__dict__, "cover_url": None})

        with _finds(no_art):
            assert refresh_song_album("s1") == "no_cover"

        song = _song()
        assert song.album == "Toys In The Attic"
        assert song.album_checked_at is not None
        assert db.get(DbAlbum, song.album_id).image_status == "not_found"

    def test_a_failed_download_is_tried_again_later(self, db, covers_dir):
        _add_song(db)

        with _finds(MATCH), patch.object(
            album_service.requests, "get", side_effect=OSError("timeout")
        ):
            assert refresh_song_album("s1") == "error"

        song = _song()
        assert song.album_id is not None
        assert song.album_checked_at is None
        assert db.get(DbAlbum, song.album_id).cover_path is None

    def test_an_unreachable_source_saves_nothing(self, db):
        _add_song(db, album="Pandora's Box")

        with patch.object(
            album_service, "find_album", side_effect=AlbumLookupError("down")
        ):
            assert refresh_song_album("s1") == "error"

        song = _song()
        assert song.album == "Pandora's Box"
        assert song.album_checked_at is None


class TestBatchFetchAlbums:
    def test_looks_songs_up_and_deletes_albums_left_unlinked(self, db, covers_dir):
        old = DbAlbum(
            title="Pandora's Box",
            source="itunes",
            source_id="9",
            cover_path="covers/album-old.jpg",
        )
        db.add(old)
        db.commit()
        covers_dir.mkdir(parents=True, exist_ok=True)
        (covers_dir / "album-old.jpg").write_bytes(b"old")
        _add_song(db, album_id=old.id)

        with _finds(MATCH), _image():
            counts = batch_fetch_albums(mode="all")

        assert counts["found"] == 1
        assert counts["albums_deleted"] == 1
        assert db.query(DbAlbum).filter(DbAlbum.source == "itunes").count() == 0
        assert not (covers_dir / "album-old.jpg").exists()

    def test_delete_unlinked_albums_keeps_linked_ones(self, db):
        kept = DbAlbum(title="Kept")
        db.add_all([kept, DbAlbum(title="Gone")])
        db.commit()
        _add_song(db, album_id=kept.id)

        assert delete_unlinked_albums() == 1
        assert [a.title for a in db.query(DbAlbum).all()] == ["Kept"]


class TestHandEditedAlbum:
    def _album(self, db):
        album = DbAlbum(title="Toys In The Attic (Deluxe)", cover_path="covers/x.jpg")
        db.add(album)
        db.commit()
        return album

    def test_a_new_album_name_is_hand_set_and_keeps_its_cover(self, client, db):
        album = self._album(db)
        _add_song(db, album=album.title, album_id=album.id)

        resp = client.patch("/api/songs/s1", json={"album": "Toys In The Attic"})

        assert resp.status_code == 200
        assert resp.json()["albumHandSet"] is True
        song = _song()
        assert song.album == "Toys In The Attic"
        assert song.album_id == album.id
        assert song.album_hand_set_at is not None

    def test_saving_the_same_name_isnt_a_hand_edit(self, client, db):
        _add_song(db, album="Toys In The Attic")

        client.patch(
            "/api/songs/s1",
            json={"title": "Sweet Emotion", "album": "Toys In The Attic"},
        )

        assert _song().album_hand_set_at is None

    def test_clearing_the_album_lets_the_lookup_find_one(self, client, db):
        album = self._album(db)
        _add_song(
            db,
            album=album.title,
            album_id=album.id,
            album_hand_set_at=utc_now(),
            album_checked_at=utc_now(),
        )

        client.patch("/api/songs/s1", json={"album": ""})

        song = _song()
        assert song.album is None
        assert song.album_id is None
        assert song.album_hand_set_at is None
        assert song.album_checked_at is None
