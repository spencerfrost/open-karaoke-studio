"""Tests for the albums API endpoint."""

from unittest.mock import MagicMock, patch

from app.db.database import SessionLocal
from app.db.models import DbAlbum


def _add_album(cover_path=None) -> int:
    with SessionLocal() as db:
        album = DbAlbum(title="Toys In The Attic", cover_path=cover_path)
        db.add(album)
        db.commit()
        return album.id


class TestAlbumCoverEndpoint:
    def test_returns_404_when_album_not_found(self, client):
        response = client.get("/api/albums/99999/cover")
        assert response.status_code == 404

    def test_returns_404_when_no_cover_path(self, client):
        album_id = _add_album(cover_path=None)

        response = client.get(f"/api/albums/{album_id}/cover")

        assert response.status_code == 404
        assert response.json()["detail"] == "Album cover not available"

    def test_returns_404_when_cover_file_is_missing(self, client, tmp_path):
        album_id = _add_album(cover_path="covers/missing.jpg")
        mock_config = MagicMock()
        mock_config.library_path = tmp_path

        with patch("app.api.albums.get_config", return_value=mock_config):
            response = client.get(f"/api/albums/{album_id}/cover")

        assert response.status_code == 404
        assert response.json()["detail"] == "Album cover file not found"

    def test_serves_cover_with_cache_header(self, client, tmp_path):
        (tmp_path / "cover.jpg").write_bytes(b"\xff\xd8\xff")
        album_id = _add_album(cover_path="cover.jpg")
        mock_config = MagicMock()
        mock_config.library_path = tmp_path

        with patch("app.api.albums.get_config", return_value=mock_config):
            response = client.get(f"/api/albums/{album_id}/cover")

        assert response.status_code == 200
        assert response.content == b"\xff\xd8\xff"
        # Without it the stage wheel revalidates every cover it scrolls past.
        assert response.headers["cache-control"] == "public, max-age=3600"


class TestArtistImageEndpoint:
    def test_serves_image_with_cache_header(self, client, tmp_path):
        image = tmp_path / "artist.jpg"
        image.write_bytes(b"\xff\xd8\xff")

        with patch(
            "app.api.artists.ArtistImageService.get_or_fetch_artist_image",
            return_value=image,
        ):
            response = client.get("/api/artists/1/image")

        assert response.status_code == 200
        assert response.headers["cache-control"] == "public, max-age=3600"

    def test_missing_image_is_404(self, client):
        with patch(
            "app.api.artists.ArtistImageService.get_or_fetch_artist_image",
            return_value=None,
        ):
            response = client.get("/api/artists/999/image")

        assert response.status_code == 404
