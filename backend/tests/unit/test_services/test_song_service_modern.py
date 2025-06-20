# backend/tests/unit/test_services/test_song_service_modern.py
"""
Modern unit tests for SongService that match the current architecture.

Tests the legitimate business logic:
- Auto-sync when database is empty
- Error handling and logging
- Type conversion DbSong → Song
- Service orchestration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from app.services.song_service import SongService
from app.exceptions import ServiceError
from app.schemas.song import Song
from app.db.models.song import DbSong


class TestSongServiceModern:
    """Modern unit tests for SongService"""

    def setup_method(self):
        """Set up test fixtures"""
        self.song_service = SongService()

    def create_mock_db_song(self, song_id="test-song-123"):
        """Create a mock DbSong with realistic data"""
        mock_song = Mock()  # Don't use spec here to allow to_dict
        mock_song.id = song_id
        mock_song.title = "Test Song"
        mock_song.artist = "Test Artist"
        mock_song.duration = 180.0
        mock_song.favorite = False
        mock_song.date_added = datetime.now(timezone.utc)

        # Create a dynamic to_dict method that reflects current attribute values
        def dynamic_to_dict():
            return {
                "id": mock_song.id,
                "title": mock_song.title,
                "artist": mock_song.artist,
                "duration": mock_song.duration,
                "favorite": mock_song.favorite,
                "dateAdded": mock_song.date_added,
                # Add optional fields to avoid validation errors
                "vocalPath": None,
                "instrumentalPath": None,
                "originalPath": None,
                "year": 2023,
                "genre": "Rock",
                "language": "English",
            }

        mock_song.to_dict = dynamic_to_dict

        return mock_song

    @patch("app.db.song_operations.get_all_songs")
    def test_get_all_songs_success(self, mock_get_all):
        """Test successful retrieval of all songs"""
        # Setup mock data
        mock_db_song = self.create_mock_db_song()
        mock_get_all.return_value = [mock_db_song]

        # Execute
        result = self.song_service.get_all_songs()

        # Assertions
        assert len(result) == 1
        assert isinstance(result[0], Song)
        assert result[0].id == "test-song-123"
        assert result[0].title == "Test Song"
        mock_get_all.assert_called_once()

    @patch("app.db.song_operations.get_all_songs")
    @patch.object(SongService, "sync_with_filesystem")
    def test_get_all_songs_auto_sync_when_empty(self, mock_sync, mock_get_all):
        """Test auto-sync feature when database is empty"""
        # Setup mocks - first call empty, second call has data
        mock_db_song = self.create_mock_db_song()
        mock_get_all.side_effect = [[], [mock_db_song]]  # Empty first, then has data
        mock_sync.return_value = 1

        # Execute
        result = self.song_service.get_all_songs()

        # Assertions
        assert len(result) == 1
        assert isinstance(result[0], Song)
        assert result[0].id == "test-song-123"
        assert result[0].title == "Test Song"
        assert mock_get_all.call_count == 2  # Called twice due to auto-sync
        mock_sync.assert_called_once()

    @patch("app.db.song_operations.get_all_songs")
    def test_get_all_songs_no_auto_sync_when_has_data(self, mock_get_all):
        """Test that auto-sync is NOT triggered when database has data"""
        # Setup mock data
        mock_db_song = self.create_mock_db_song()
        mock_get_all.return_value = [mock_db_song]

        with patch.object(self.song_service, "sync_with_filesystem") as mock_sync:
            # Execute
            result = self.song_service.get_all_songs()

            # Assertions
            assert len(result) == 1
            mock_get_all.assert_called_once()  # Only called once
            mock_sync.assert_not_called()  # Sync should NOT be called

    @patch("app.db.song_operations.get_all_songs")
    def test_get_all_songs_database_error(self, mock_get_all):
        """Test error handling when database operation fails"""
        # Setup mock to raise exception
        mock_get_all.side_effect = Exception("Database error")

        # Execute and assert exception
        with pytest.raises(ServiceError) as exc_info:
            self.song_service.get_all_songs()

        assert "Failed to retrieve songs" in str(exc_info.value)

    @patch("app.db.song_operations.get_song")
    def test_get_song_by_id_success(self, mock_get_song):
        """Test successful song retrieval by ID"""
        # Setup mock data
        song_id = "test-song-123"
        mock_db_song = self.create_mock_db_song(song_id)
        mock_get_song.return_value = mock_db_song

        # Execute
        result = self.song_service.get_song_by_id(song_id)

        # Assertions
        assert result is not None
        assert isinstance(result, Song)
        assert result.id == song_id
        assert result.title == "Test Song"
        mock_get_song.assert_called_once_with(song_id)

    @patch("app.db.song_operations.get_song")
    def test_get_song_by_id_not_found(self, mock_get_song):
        """Test behavior when song is not found"""
        # Setup mock to return None
        song_id = "nonexistent-song"
        mock_get_song.return_value = None

        # Execute
        result = self.song_service.get_song_by_id(song_id)

        # Assertions
        assert result is None
        mock_get_song.assert_called_once_with(song_id)

    @patch("app.db.song_operations.get_song")
    def test_get_song_by_id_database_error(self, mock_get_song):
        """Test error handling when getting song by ID fails"""
        # Setup mock to raise exception
        song_id = "test-song-123"
        mock_get_song.side_effect = Exception("Database error")

        # Execute and assert exception
        with pytest.raises(ServiceError) as exc_info:
            self.song_service.get_song_by_id(song_id)

        assert "Failed to retrieve song" in str(exc_info.value)

    @patch("app.db.song_operations.get_all_songs")
    def test_search_songs_empty_query_returns_all(self, mock_get_all):
        """Test that empty search query returns all songs"""
        # Setup mock data
        mock_db_song = self.create_mock_db_song()
        mock_get_all.return_value = [mock_db_song]

        # Execute with empty query
        result = self.song_service.search_songs("")

        # Assertions
        assert len(result) == 1
        assert isinstance(result[0], Song)
        assert result[0].id == "test-song-123"
        assert result[0].title == "Test Song"
        mock_get_all.assert_called_once()

    @patch("app.db.song_operations.get_all_songs")
    def test_search_songs_filters_by_query(self, mock_get_all):
        """Test that search properly filters songs by query"""
        # Setup mock data - songs that should match and not match
        matching_song = self.create_mock_db_song("match-1")
        matching_song.title = "Bohemian Rhapsody"
        matching_song.artist = "Queen"

        non_matching_song = self.create_mock_db_song("no-match-1")
        non_matching_song.title = "Different Song"
        non_matching_song.artist = "Different Artist"

        mock_get_all.return_value = [matching_song, non_matching_song]

        # Execute with search query
        result = self.song_service.search_songs("queen")

        # Assertions - should only return matching song
        assert len(result) == 1
        assert isinstance(result[0], Song)
        assert result[0].id == "match-1"
        assert result[0].title == "Bohemian Rhapsody"

    @patch("app.db.song_operations.get_all_songs")
    def test_search_songs_case_insensitive(self, mock_get_all):
        """Test that search is case insensitive"""
        # Setup mock data
        mock_db_song = self.create_mock_db_song()
        mock_db_song.title = "Bohemian Rhapsody"
        mock_db_song.artist = "Queen"
        mock_get_all.return_value = [mock_db_song]

        # Execute with different case variations
        for query in ["QUEEN", "queen", "Queen", "rhapsody", "RHAPSODY"]:
            result = self.song_service.search_songs(query)
            assert len(result) == 1, f"Query '{query}' should match"

    @patch("app.db.song_operations.get_song")
    @patch("app.db.song_operations.delete_song")
    def test_delete_song_success(self, mock_delete, mock_get_song):
        """Test successful song deletion"""
        # Setup mocks
        song_id = "song-to-delete"
        mock_existing_song = self.create_mock_db_song(song_id)
        mock_get_song.return_value = mock_existing_song
        mock_delete.return_value = True

        # Execute
        result = self.song_service.delete_song(song_id)

        # Assertions
        assert result is True
        mock_get_song.assert_called_once_with(song_id)
        mock_delete.assert_called_once_with(song_id)

    @patch("app.db.song_operations.get_song")
    @patch("app.db.song_operations.delete_song")
    def test_delete_song_not_found(self, mock_delete, mock_get_song):
        """Test deletion when song doesn't exist"""
        # Setup mock to return None (song not found)
        song_id = "nonexistent-song"
        mock_get_song.return_value = None

        # Execute
        result = self.song_service.delete_song(song_id)

        # Assertions
        assert result is False
        mock_get_song.assert_called_once_with(song_id)
        mock_delete.assert_not_called()  # Should not attempt to delete

    @patch("app.db.song_operations.get_song")
    def test_delete_song_database_error(self, mock_get_song):
        """Test error handling during song deletion"""
        # Setup mock to raise exception
        song_id = "test-song"
        mock_get_song.side_effect = Exception("Database error")

        # Execute and assert exception
        with pytest.raises(ServiceError) as exc_info:
            self.song_service.delete_song(song_id)

        assert f"Failed to delete song {song_id}" in str(exc_info.value)

    @patch("app.db.song_operations.sync_songs_with_filesystem")
    def test_sync_with_filesystem_success(self, mock_sync):
        """Test successful filesystem sync"""
        # Setup mock
        mock_sync.return_value = 5

        # Execute
        result = self.song_service.sync_with_filesystem()

        # Assertions
        assert result == 5
        mock_sync.assert_called_once()

    @patch("app.db.song_operations.sync_songs_with_filesystem")
    def test_sync_with_filesystem_error(self, mock_sync):
        """Test error handling during filesystem sync"""
        # Setup mock to raise exception
        mock_sync.side_effect = Exception("Filesystem sync error")

        # Execute and assert exception
        with pytest.raises(ServiceError) as exc_info:
            self.song_service.sync_with_filesystem()

        assert "Failed to sync with filesystem" in str(exc_info.value)
