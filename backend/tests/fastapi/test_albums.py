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
