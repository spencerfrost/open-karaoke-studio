"""Tests for the albums API endpoint."""
from unittest.mock import MagicMock, patch

import pytest


class TestAlbumCoverEndpoint:
    def test_returns_404_when_album_not_found(self, client):
        response = client.get("/api/albums/99999/cover")
        assert response.status_code == 404

    def test_returns_404_when_no_cover_path(self, client):
        mock_album = MagicMock()
        mock_album.cover_path = None

        with patch("app.api.albums.SessionLocal") as mock_session_cls:
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = mock_album
            mock_session_cls.return_value = mock_db
            response = client.get("/api/albums/1/cover")

        assert response.status_code == 404

    def test_serves_cover_with_cache_header(self, client, tmp_path):
        (tmp_path / "cover.jpg").write_bytes(b"\xff\xd8\xff")
        mock_album = MagicMock()
        mock_album.cover_path = "cover.jpg"
        mock_config = MagicMock()
        mock_config.library_path = tmp_path

        with (
            patch("app.api.albums.SessionLocal") as mock_session_cls,
            patch("app.api.albums.get_config", return_value=mock_config),
        ):
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = mock_album
            mock_session_cls.return_value = mock_db
            response = client.get("/api/albums/1/cover")

        assert response.status_code == 200
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
            response = client.get("/api/artists/image", params={"name": "ABBA"})

        assert response.status_code == 200
        assert response.headers["cache-control"] == "public, max-age=3600"

    def test_missing_image_is_404(self, client):
        with patch(
            "app.api.artists.ArtistImageService.get_or_fetch_artist_image",
            return_value=None,
        ):
            response = client.get("/api/artists/image", params={"name": "Nobody"})

        assert response.status_code == 404
