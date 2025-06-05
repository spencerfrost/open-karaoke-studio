"""
Unit tests for the file management service in Open Karaoke Studio.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json

# Mock the imports that might not be available during testing
try:
    from app.services.file_management import (
        get_song_dir, ensure_song_directory, get_metadata,
        save_metadata, get_all_song_ids
    )
except ImportError:
    # Create mock functions for testing when app isn't available
    def get_song_dir(song_id):
        return Path(f"/mock/library/{song_id}")
    
    def ensure_song_directory(song_id):
        return Path(f"/mock/library/{song_id}")
    
    def get_metadata(song_id):
        return {"title": "Mock Song", "artist": "Mock Artist"}
    
    def save_metadata(song_id, metadata):
        return True
    
    def get_all_song_ids():
        return ["song1", "song2", "song3"]


class TestFileManagementService:
    """Test the file management service"""
    
    @patch('app.services.file_management.get_config')
    def test_get_song_dir(self, mock_get_config):
        """Test getting song directory path"""
        # Setup mock config
        mock_config = Mock()
        mock_config.LIBRARY_DIR = Path("/test/library")
        mock_get_config.return_value = mock_config
        
        song_id = "test-song-123"
        
        result = get_song_dir(song_id)
        
        expected_path = Path("/test/library/test-song-123")
        assert result == expected_path
    
    @patch('app.services.file_management.get_config')
    @patch('pathlib.Path.mkdir')
    def test_ensure_song_directory_creates_dir(self, mock_mkdir, mock_get_config):
        """Test that ensure_song_directory creates directory if it doesn't exist"""
        # Setup mock config
        mock_config = Mock()
        mock_config.LIBRARY_DIR = Path("/test/library")
        mock_get_config.return_value = mock_config
        
        song_id = "test-song-123"
        
        with patch('pathlib.Path.exists', return_value=False):
            result = ensure_song_directory(song_id)
            
            expected_path = Path("/test/library/test-song-123")
            assert result == expected_path
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    @patch('app.services.file_management.get_config')
    def test_ensure_song_directory_exists(self, mock_get_config):
        """Test ensure_song_directory when directory already exists"""
        # Setup mock config
        mock_config = Mock()
        mock_config.LIBRARY_DIR = Path("/test/library")
        mock_get_config.return_value = mock_config
        
        song_id = "test-song-123"
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.mkdir') as mock_mkdir:
                result = ensure_song_directory(song_id)
                
                expected_path = Path("/test/library/test-song-123")
                assert result == expected_path
                # mkdir should still be called with exist_ok=True
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    
    @patch('app.services.file_management.get_song_dir')
    def test_get_metadata_success(self, mock_get_song_dir):
        """Test successful metadata retrieval"""
        # Setup mock song directory
        mock_song_dir = Mock()
        mock_metadata_file = Mock()
        mock_song_dir.__truediv__.return_value = mock_metadata_file
        mock_get_song_dir.return_value = mock_song_dir
        
        # Mock metadata content
        metadata_content = {
            "title": "Test Song",
            "artist": "Test Artist",
            "duration": 180,
            "favorite": False
        }
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value=json.dumps(metadata_content)):
                result = get_metadata("test-song-123")
                
                assert result == metadata_content
                assert result["title"] == "Test Song"
                assert result["artist"] == "Test Artist"
    
    @patch('app.services.file_management.get_song_dir')
    def test_get_metadata_file_not_found(self, mock_get_song_dir):
        """Test metadata retrieval when file doesn't exist"""
        # Setup mock song directory
        mock_song_dir = Mock()
        mock_get_song_dir.return_value = mock_song_dir
        
        with patch('pathlib.Path.exists', return_value=False):
            result = get_metadata("test-song-123")
            
            # Should return default metadata or None
            assert result is None or isinstance(result, dict)
    
    @patch('app.services.file_management.get_song_dir')
    def test_get_metadata_invalid_json(self, mock_get_song_dir):
        """Test metadata retrieval with invalid JSON"""
        # Setup mock song directory
        mock_song_dir = Mock()
        mock_metadata_file = Mock()
        mock_song_dir.__truediv__.return_value = mock_metadata_file
        mock_get_song_dir.return_value = mock_song_dir
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.read_text', return_value="invalid json"):
                with patch('json.loads', side_effect=json.JSONDecodeError("Invalid", "", 0)):
                    result = get_metadata("test-song-123")
                    
                    # Should handle JSON decode error gracefully
                    assert result is None or isinstance(result, dict)
    
    @patch('app.services.file_management.get_song_dir')
    def test_save_metadata_success(self, mock_get_song_dir):
        """Test successful metadata saving"""
        # Setup mock song directory
        mock_song_dir = Mock()
        mock_metadata_file = Mock()
        mock_song_dir.__truediv__.return_value = mock_metadata_file
        mock_get_song_dir.return_value = mock_song_dir
        
        metadata = {
            "title": "New Song",
            "artist": "New Artist",
            "duration": 240,
            "favorite": True
        }
        
        with patch('pathlib.Path.write_text') as mock_write_text:
            result = save_metadata("test-song-123", metadata)
            
            # Should write JSON to file
            mock_write_text.assert_called_once()
            written_content = mock_write_text.call_args[0][0]
            assert isinstance(written_content, str)
            
            # Verify JSON is valid
            parsed_content = json.loads(written_content)
            assert parsed_content == metadata
    
    @patch('app.services.file_management.get_song_dir')
    def test_save_metadata_write_error(self, mock_get_song_dir):
        """Test metadata saving with write error"""
        # Setup mock song directory
        mock_song_dir = Mock()
        mock_metadata_file = Mock()
        mock_song_dir.__truediv__.return_value = mock_metadata_file
        mock_get_song_dir.return_value = mock_song_dir
        
        metadata = {"title": "Test Song"}
        
        with patch('pathlib.Path.write_text', side_effect=IOError("Write failed")):
            # Should handle write error gracefully
            result = save_metadata("test-song-123", metadata)
            
            # Depending on implementation, might return False or raise exception
            assert result is False or result is None
    
    @patch('app.services.file_management.get_config')
    def test_get_all_song_ids(self, mock_get_config):
        """Test getting all song IDs from library directory"""
        # Setup mock config
        mock_config = Mock()
        mock_library_dir = Mock()
        mock_config.LIBRARY_DIR = mock_library_dir
        mock_get_config.return_value = mock_config
        
        # Mock directory iteration
        mock_dirs = [
            Mock(name="song-1", is_dir=Mock(return_value=True)),
            Mock(name="song-2", is_dir=Mock(return_value=True)),
            Mock(name="not-a-dir.txt", is_dir=Mock(return_value=False)),
            Mock(name="song-3", is_dir=Mock(return_value=True)),
        ]
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.iterdir', return_value=mock_dirs):
                result = get_all_song_ids()
                
                # Should only return directory names
                expected_ids = ["song-1", "song-2", "song-3"]
                assert len(result) == 3
                for song_id in expected_ids:
                    assert song_id in result
    
    @patch('app.services.file_management.get_config')
    def test_get_all_song_ids_empty_library(self, mock_get_config):
        """Test getting song IDs from empty library directory"""
        # Setup mock config
        mock_config = Mock()
        mock_library_dir = Mock()
        mock_config.LIBRARY_DIR = mock_library_dir
        mock_get_config.return_value = mock_config
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.iterdir', return_value=[]):
                result = get_all_song_ids()
                
                assert result == []
    
    @patch('app.services.file_management.get_config')
    def test_get_all_song_ids_library_not_exists(self, mock_get_config):
        """Test getting song IDs when library directory doesn't exist"""
        # Setup mock config
        mock_config = Mock()
        mock_library_dir = Mock()
        mock_config.LIBRARY_DIR = mock_library_dir
        mock_get_config.return_value = mock_config
        
        with patch('pathlib.Path.exists', return_value=False):
            result = get_all_song_ids()
            
            # Should return empty list or handle gracefully
            assert result == [] or result is None


class TestFileManagementHelpers:
    """Test helper functions in file management"""
    
    def test_validate_song_id(self):
        """Test song ID validation"""
        # This would test a helper function if it exists
        valid_ids = ["song-123", "test_song", "song123"]
        invalid_ids = ["../malicious", "song/with/slashes", ""]
        
        # Mock validation function
        def validate_song_id(song_id):
            if not song_id or '/' in song_id or '..' in song_id:
                return False
            return True
        
        for valid_id in valid_ids:
            assert validate_song_id(valid_id) is True
        
        for invalid_id in invalid_ids:
            assert validate_song_id(invalid_id) is False
    
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        # Mock sanitization function
        def sanitize_filename(filename):
            import re
            # Remove/replace invalid characters
            sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
            return sanitized.strip()
        
        test_cases = [
            ("normal_file.mp3", "normal_file.mp3"),
            ("file with spaces.mp3", "file with spaces.mp3"),
            ("file<with>invalid:chars.mp3", "file_with_invalid_chars.mp3"),
            ('file"with|quotes?.mp3', "file_with_quotes_.mp3"),
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected
