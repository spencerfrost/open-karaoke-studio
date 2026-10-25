"""Tests for the artist endpoints (app/api/artists.py).

Rows are real; only ArtistImageService is mocked, since it talks to Discogs.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.db.models import DbArtist, DbSong, DbSongArtist


@pytest.fixture
def image_service():
    with patch("app.api.artists.ArtistImageService") as service_class:
        service = service_class.return_value
        service.get_or_fetch_artist_image = AsyncMock(return_value=None)
        service.search_artist_images = AsyncMock(return_value=[])
        service.set_image_from_url = AsyncMock(return_value=None)
        yield service


def _artist(db, name, display_name=None):
    artist = DbArtist(name=name.lower(), display_name=display_name or name)
    db.add(artist)
    db.commit()
    return artist


def _credited_song(db, song_id, *artists):
    """A song credited to the given artists, the first one primary."""
    db.add(
        DbSong(
            id=song_id,
            title=song_id,
            artist=" & ".join(a.display_name for a in artists),
            artist_id=artists[0].id,
        )
    )
    for order, artist in enumerate(artists):
        db.add(
            DbSongArtist(
                song_id=song_id,
                artist_id=artist.id,
                role="primary",
                display_order=order,
            )
        )
    db.commit()


class TestUpdateArtist:
    def test_renames_display_name(self, client, db):
        artist = _artist(db, "Queen")

        response = client.patch(
            f"/api/artists/{artist.id}", json={"display_name": "QUEEN"}
        )

        assert response.status_code == 200
        assert response.json() == {
            "id": artist.id,
            "name": "queen",
            "display_name": "QUEEN",
        }
        db.expire_all()
        assert db.get(DbArtist, artist.id).display_name == "QUEEN"

    def test_unknown_artist_is_404(self, client):
        response = client.patch("/api/artists/999", json={"display_name": "X"})

        assert response.status_code == 404


class TestDeleteArtist:
    def test_deletes_own_songs_and_unlinks_shared_ones(self, client, db):
        queen = _artist(db, "Queen")
        bowie = _artist(db, "David Bowie")
        _credited_song(db, "solo", queen)
        _credited_song(db, "duet", bowie, queen)
        queen_id, bowie_id = queen.id, bowie.id

        response = client.delete(f"/api/artists/{queen_id}")

        assert response.status_code == 200
        assert response.json() == {"deleted_songs": 1, "unlinked_songs": 1}
        db.expire_all()
        assert db.get(DbArtist, queen_id) is None
        assert db.get(DbSong, "solo") is None
        duet_credits = db.query(DbSongArtist).filter_by(song_id="duet").all()
        assert [c.artist_id for c in duet_credits] == [bowie_id]

    def test_unknown_artist_is_404(self, client):
        assert client.delete("/api/artists/999").status_code == 404


class TestArtistImage:
    def test_serves_the_cached_file(self, client, image_service, tmp_path):
        image = tmp_path / "queen.jpg"
        image.write_bytes(b"jpeg bytes")
        image_service.get_or_fetch_artist_image.return_value = image

        response = client.get("/api/artists/42/image")

        assert response.status_code == 200
        assert response.content == b"jpeg bytes"
        assert response.headers["content-type"] == "image/jpeg"
        assert response.headers["cache-control"] == "public, max-age=3600"
        image_service.get_or_fetch_artist_image.assert_awaited_once_with(42)

    def test_no_image_is_404(self, client, image_service):
        response = client.get("/api/artists/999/image")

        assert response.status_code == 404


class TestSearchArtistImages:
    def test_returns_candidates(self, client, db, image_service):
        artist = _artist(db, "Queen")
        candidates = [{"url": "https://example.com/queen.jpg"}]
        image_service.search_artist_images.return_value = candidates

        response = client.get(
            f"/api/artists/{artist.id}/images/search", params={"q": "Queen band"}
        )

        assert response.status_code == 200
        assert response.json() == {"results": candidates}
        image_service.search_artist_images.assert_awaited_once_with("Queen band")

    def test_unknown_artist_is_404(self, client, image_service):
        response = client.get("/api/artists/999/images/search", params={"q": "x"})

        assert response.status_code == 404
        image_service.search_artist_images.assert_not_awaited()


class TestSetArtistImage:
    def test_saves_image_from_url(self, client, db, image_service, tmp_path):
        artist = _artist(db, "Queen")
        image_service.set_image_from_url.return_value = tmp_path / "queen.jpg"

        response = client.post(
            f"/api/artists/{artist.id}/image",
            json={"url": "https://example.com/queen.jpg"},
        )

        assert response.status_code == 200
        assert response.json() == {"success": True}
        image_service.set_image_from_url.assert_awaited_once_with(
            artist.id, "https://example.com/queen.jpg"
        )

    def test_failed_download_is_422(self, client, db, image_service):
        artist = _artist(db, "Queen")

        response = client.post(
            f"/api/artists/{artist.id}/image",
            json={"url": "https://example.com/broken.jpg"},
        )

        assert response.status_code == 422

    def test_unknown_artist_is_404(self, client, image_service):
        response = client.post(
            "/api/artists/999/image", json={"url": "https://example.com/x.jpg"}
        )

        assert response.status_code == 404
        image_service.set_image_from_url.assert_not_awaited()


class TestSplitArtistCredits:
    def test_replaces_credits_on_every_song(self, client, db):
        combined = _artist(db, "Simon & Garfunkel")
        combined_id = combined.id
        _credited_song(db, "boxer", combined)
        _credited_song(db, "mrs-robinson", combined)

        response = client.post(
            f"/api/artists/{combined_id}/split-credits",
            json={
                "credits": [
                    {"name": "Simon", "role": "primary"},
                    {"name": "Garfunkel", "role": "primary"},
                    {"name": "Choir", "role": "featured"},
                ]
            },
        )

        assert response.status_code == 200
        assert response.json() == {"updated": 2}
        db.expire_all()
        simon = db.query(DbArtist).filter_by(name="simon").one()
        song = db.get(DbSong, "boxer")
        assert song.artist == "Simon & Garfunkel feat. Choir"
        assert song.artist_id == simon.id
        assert song.metadata_confirmed_at is not None
        credits = sorted(song.song_artists, key=lambda c: c.display_order)
        assert [(c.artist_rel.display_name, c.role) for c in credits] == [
            ("Simon", "primary"),
            ("Garfunkel", "primary"),
            ("Choir", "featured"),
        ]
        # Nothing refers to the combined artist any more
        assert db.get(DbArtist, combined_id) is None

    def test_where_it_was_featured_the_split_artists_are_featured(self, client, db):
        main = _artist(db, "Chase & Status")
        guests = _artist(db, "Popcaan & IRah")
        _credited_song(db, "song", main, guests)
        db.query(DbSongArtist).filter_by(artist_id=guests.id).update(
            {"role": "featured"}
        )
        db.commit()

        response = client.post(
            f"/api/artists/{guests.id}/split-credits",
            json={
                "credits": [
                    {"name": "Popcaan", "role": "primary"},
                    {"name": "IRah", "role": "featured"},
                ]
            },
        )

        assert response.status_code == 200
        db.expire_all()
        song = db.get(DbSong, "song")
        credits = sorted(song.song_artists, key=lambda c: c.display_order)
        assert [(c.artist_rel.display_name, c.role) for c in credits] == [
            ("Chase & Status", "primary"),
            ("Popcaan", "featured"),
            ("IRah", "featured"),
        ]
        assert song.artist == "Chase & Status feat. Popcaan, IRah"
        assert song.artist_id == main.id

    def test_requires_a_primary_credit(self, client, db):
        combined = _artist(db, "Simon & Garfunkel")

        response = client.post(
            f"/api/artists/{combined.id}/split-credits",
            json={"credits": [{"name": "Choir", "role": "featured"}]},
        )

        assert response.status_code == 400

    def test_unknown_artist_is_404(self, client):
        response = client.post(
            "/api/artists/999/split-credits",
            json={"credits": [{"name": "Simon", "role": "primary"}]},
        )

        assert response.status_code == 404


class TestMergeArtist:
    def test_moves_credits_and_keeps_the_old_name(self, client, db):
        old = _artist(db, "Dixie Chicks")
        new = _artist(db, "The Chicks")
        old_id = old.id
        _credited_song(db, "wide-open-spaces", old)

        response = client.post(f"/api/artists/{old_id}/merge-into/{new.id}")

        assert response.status_code == 200
        assert response.json() == {"id": new.id, "name": "The Chicks", "moved": 1}
        db.expire_all()
        assert db.get(DbArtist, old_id) is None
        song = db.get(DbSong, "wide-open-spaces")
        assert song.artist_id == new.id
        assert [c.artist_id for c in song.song_artists] == [new.id]
        # Song text is left as it is
        assert song.artist == "Dixie Chicks"
        assert [a.name for a in db.get(DbArtist, new.id).aliases] == ["Dixie Chicks"]

    def test_into_itself_is_400(self, client, db):
        artist = _artist(db, "Queen")
        response = client.post(f"/api/artists/{artist.id}/merge-into/{artist.id}")
        assert response.status_code == 400

    def test_unknown_artist_is_404(self, client, db):
        artist = _artist(db, "Queen")
        response = client.post(f"/api/artists/{artist.id}/merge-into/999")
        assert response.status_code == 404
