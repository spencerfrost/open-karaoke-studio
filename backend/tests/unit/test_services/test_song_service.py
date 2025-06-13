"""
Unit tests for Song Service Layer
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from app.services.song_service import SongService
from app.exceptions import ServiceError, NotFoundError
from app.db.models import Song, SongMetadata, DbSong


class TestSongService:
    """Unit tests for SongService"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.song_service = SongService()
    
    @patch('app.services.song_service.database')
    def test_get_all_songs_success(self, mock_database):
        """Test successful retrieval of all songs"""
        # Setup mock data
        mock_db_song = Mock(spec=DbSong)
        mock_pydantic_song = Mock(spec=Song)
        mock_db_song.to_pydantic.return_value = mock_pydantic_song
        mock_database.get_all_songs.return_value = [mock_db_song]
        
        # Execute
        result = self.song_service.get_all_songs()
        
        # Assertions
        assert result == [mock_pydantic_song]
        mock_database.get_all_songs.assert_called_once()
        mock_db_song.to_pydantic.assert_called_once()
    
    @patch('app.services.song_service.database')
    @patch('app.services.song_service.logger')
    def test_get_all_songs_empty_triggers_sync(self, mock_logger, mock_database):
        """Test that empty database triggers filesystem sync"""
        # Setup mocks - first call empty, second call has songs
        mock_db_song = Mock(spec=DbSong)
        mock_pydantic_song = Mock(spec=Song)
        mock_db_song.to_pydantic.return_value = mock_pydantic_song
        
        mock_database.get_all_songs.side_effect = [[], [mock_db_song]]
        mock_database.sync_songs_with_filesystem.return_value = 1
        
        # Execute
        result = self.song_service.get_all_songs()
        
        # Assertions
        assert result == [mock_pydantic_song]
        assert mock_database.get_all_songs.call_count == 2
        mock_database.sync_songs_with_filesystem.assert_called_once()
        mock_logger.info.assert_called()
    
    @patch('app.services.song_service.database')
    @patch('app.services.song_service.logger')
    def test_get_all_songs_database_error(self, mock_logger, mock_database):
        """Test handling of database errors"""
        # Setup mock to raise exception
        mock_database.get_all_songs.side_effect = Exception("Database connection failed")
        
        # Execute and assert exception
        with pytest.raises(ServiceError) as exc_info:
            self.song_service.get_all_songs()
        
        assert "Failed to retrieve songs" in str(exc_info.value)
        mock_logger.error.assert_called()
    
    @patch('app.services.song_service.database')
    def test_get_song_by_id_success(self, mock_database):
        """Test successful retrieval of song by ID"""
        # Setup mock data
        song_id = "test-song-123"
        mock_db_song = Mock(spec=DbSong)
        mock_pydantic_song = Mock(spec=Song)
        mock_db_song.to_pydantic.return_value = mock_pydantic_song
        mock_database.get_song.return_value = mock_db_song
        
        # Execute
        result = self.song_service.get_song_by_id(song_id)
        
        # Assertions
        assert result == mock_pydantic_song
        mock_database.get_song.assert_called_once_with(song_id)
        mock_db_song.to_pydantic.assert_called_once()
    
    @patch('app.services.song_service.database')
    def test_get_song_by_id_not_found(self, mock_database):
        """Test retrieval when song not found"""
        # Setup mock to return None
        song_id = "nonexistent-song"
        mock_database.get_song.return_value = None
        
        # Execute
        result = self.song_service.get_song_by_id(song_id)
        
        # Assertions
        assert result is None
        mock_database.get_song.assert_called_once_with(song_id)
    
    @patch('app.services.song_service.database')
    @patch('app.services.song_service.logger')
    def test_get_song_by_id_database_error(self, mock_logger, mock_database):
        """Test handling of database errors when getting song by ID"""
        # Setup mock to raise exception
        song_id = "test-song-123"
        mock_database.get_song.side_effect = Exception("Database error")
        
        # Execute and assert exception
        with pytest.raises(ServiceError) as exc_info:
            self.song_service.get_song_by_id(song_id)
        
        assert f"Failed to retrieve song {song_id}" in str(exc_info.value)
        mock_logger.error.assert_called()
    
    @patch('app.services.song_service.database')
    def test_search_songs_success(self, mock_database):
        """Test successful song search"""
        # Setup mock data
        query = "test"
        mock_db_song1 = Mock(spec=DbSong)
        mock_db_song1.title = "Test Song"
        mock_db_song1.artist = "Test Artist"
        mock_pydantic_song1 = Mock(spec=Song)
        mock_db_song1.to_pydantic.return_value = mock_pydantic_song1
        
        mock_db_song2 = Mock(spec=DbSong)
        mock_db_song2.title = "Another Song"
        mock_db_song2.artist = "Different Artist"
        
        mock_database.get_all_songs.return_value = [mock_db_song1, mock_db_song2]
        
        # Execute
        result = self.song_service.search_songs(query)
        
        # Assertions - should return only matching song
        assert len(result) == 1
        assert result[0] == mock_pydantic_song1
        mock_database.get_all_songs.assert_called_once()
    
    @patch('app.services.song_service.database')
    def test_search_songs_empty_query(self, mock_database):
        """Test search with empty query returns all songs"""
        # Setup mock data
        mock_db_song = Mock(spec=DbSong)
        mock_pydantic_song = Mock(spec=Song)
        mock_db_song.to_pydantic.return_value = mock_pydantic_song
        mock_database.get_all_songs.return_value = [mock_db_song]
        
        # Execute with empty query
        result = self.song_service.search_songs("")
        
        # Assertions
        assert len(result) == 1
        assert result[0] == mock_pydantic_song
    
    @patch('app.services.song_service.database')
    @patch('app.services.song_service.logger')
    def test_search_songs_database_error(self, mock_logger, mock_database):
        """Test handling of database errors during search"""
        # Setup mock to raise exception
        mock_database.get_all_songs.side_effect = Exception("Database error")
        
        # Execute and assert exception
        with pytest.raises(ServiceError) as exc_info:
            self.song_service.search_songs("test")
        
        assert "Failed to search songs" in str(exc_info.value)
        mock_logger.error.assert_called()
    
    @patch('app.services.song_service.database')
    def test_create_song_from_metadata_success(self, mock_database):
        """Test successful song creation from metadata"""
        # Setup mock data
        song_id = "new-song-123"
        metadata = SongMetadata(
            title="New Song",
            artist="New Artist",
            dateAdded=datetime.now(timezone.utc)
        )
        mock_db_song = Mock(spec=DbSong)
        mock_pydantic_song = Mock(spec=Song)
        mock_db_song.to_pydantic.return_value = mock_pydantic_song
        mock_database.create_or_update_song.return_value = mock_db_song
        
        # Execute
        result = self.song_service.create_song_from_metadata(song_id, metadata)
        
        # Assertions
        assert result == mock_pydantic_song
        mock_database.create_or_update_song.assert_called_once_with(song_id, metadata)
        mock_db_song.to_pydantic.assert_called_once()
    
    @patch('app.services.song_service.database')
    @patch('app.services.song_service.logger')
    def test_create_song_from_metadata_database_failure(self, mock_logger, mock_database):
        """Test handling of database failures during song creation"""
        # Setup mock to return None (creation failed)
        song_id = "new-song-123"
        metadata = SongMetadata(title="New Song", artist="New Artist")
        mock_database.create_or_update_song.return_value = None
        
        # Execute and assert exception
        with pytest.raises(ServiceError) as exc_info:
            self.song_service.create_song_from_metadata(song_id, metadata)
        
        assert f"Failed to create song {song_id}" in str(exc_info.value)
    
    @patch('app.services.song_service.database')
    def test_update_song_metadata_success(self, mock_database):
        """Test successful song metadata update"""
        # Setup mock data
        song_id = "existing-song-123"
        metadata = SongMetadata(title="Updated Title", artist="Updated Artist")
        
        mock_existing_song = Mock(spec=DbSong)
        mock_updated_song = Mock(spec=DbSong)
        mock_pydantic_song = Mock(spec=Song)
        mock_updated_song.to_pydantic.return_value = mock_pydantic_song
        
        mock_database.get_song.return_value = mock_existing_song
        mock_database.create_or_update_song.return_value = mock_updated_song
        
        # Execute
        result = self.song_service.update_song_metadata(song_id, metadata)
        
        # Assertions
        assert result == mock_pydantic_song
        mock_database.get_song.assert_called_once_with(song_id)
        mock_database.create_or_update_song.assert_called_once_with(song_id, metadata)
    
    @patch('app.services.song_service.database')
    def test_update_song_metadata_not_found(self, mock_database):
        """Test update when song doesn't exist"""
        # Setup mock to return None (song not found)
        song_id = "nonexistent-song"
        metadata = SongMetadata(title="Updated Title", artist="Updated Artist")
        mock_database.get_song.return_value = None
        
        # Execute
        result = self.song_service.update_song_metadata(song_id, metadata)
        
        # Assertions
        assert result is None
        mock_database.get_song.assert_called_once_with(song_id)
        mock_database.create_or_update_song.assert_not_called()
    
    @patch('app.services.song_service.database')
    def test_delete_song_success(self, mock_database):
        """Test successful song deletion"""
        # Setup mock data
        song_id = "song-to-delete"
        mock_existing_song = Mock(spec=DbSong)
        mock_database.get_song.return_value = mock_existing_song
        mock_database.delete_song.return_value = True
        
        # Execute
        result = self.song_service.delete_song(song_id)
        
        # Assertions
        assert result is True
        mock_database.get_song.assert_called_once_with(song_id)
        mock_database.delete_song.assert_called_once_with(song_id)
    
    @patch('app.services.song_service.database')
    def test_delete_song_not_found(self, mock_database):
        """Test deletion when song doesn't exist"""
        # Setup mock to return None (song not found)
        song_id = "nonexistent-song"
        mock_database.get_song.return_value = None
        
        # Execute
        result = self.song_service.delete_song(song_id)
        
        # Assertions
        assert result is False
        mock_database.get_song.assert_called_once_with(song_id)
        mock_database.delete_song.assert_not_called()
    
    @patch('app.services.song_service.database')
    @patch('app.services.song_service.logger')
    def test_delete_song_database_error(self, mock_logger, mock_database):
        """Test handling of database errors during deletion"""
        # Setup mock to raise exception
        song_id = "song-to-delete"
        mock_database.get_song.side_effect = Exception("Database error")
        
        # Execute and assert exception
        with pytest.raises(ServiceError) as exc_info:
            self.song_service.delete_song(song_id)
        
        assert f"Failed to delete song {song_id}" in str(exc_info.value)
        mock_logger.error.assert_called()
    
    @patch('app.services.song_service.database')
    def test_sync_with_filesystem_success(self, mock_database):
        """Test successful filesystem sync"""
        # Setup mock
        mock_database.sync_songs_with_filesystem.return_value = 5
        
        # Execute
        result = self.song_service.sync_with_filesystem()
        
        # Assertions
        assert result == 5
        mock_database.sync_songs_with_filesystem.assert_called_once()
    
    @patch('app.services.song_service.database')
    @patch('app.services.song_service.logger')
    def test_sync_with_filesystem_error(self, mock_logger, mock_database):
        """Test handling of filesystem sync errors"""
        # Setup mock to raise exception
        mock_database.sync_songs_with_filesystem.side_effect = Exception("Sync error")
        
        # Execute and assert exception
        with pytest.raises(ServiceError) as exc_info:
            self.song_service.sync_with_filesystem()
        
        assert "Failed to sync with filesystem" in str(exc_info.value)
        mock_logger.error.assert_called()
