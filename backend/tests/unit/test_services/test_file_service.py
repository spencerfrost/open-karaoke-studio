"""
Unit tests for the FileService in Open Karaoke Studio.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.exceptions import ServiceError
from app.services.file_service import FileService


class TestFileService:
    """Test the FileService class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.file_service = FileService(base_library_dir=self.temp_dir)

    def teardown_method(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_init_with_custom_library_dir(self):
        """Test FileService initialization with custom library directory"""
        custom_dir = Path("/custom/library")
        service = FileService(base_library_dir=custom_dir)
        assert service.base_library_dir == custom_dir

    @patch("app.services.file_service.get_config")
    def test_init_with_default_library_dir(self, mock_get_config):
        """Test FileService initialization with default library directory from config"""
        mock_config = Mock()
        mock_config.LIBRARY_DIR = Path("/default/library")
        mock_get_config.return_value = mock_config

        service = FileService()
        assert service.base_library_dir == Path("/default/library")

    def test_ensure_library_exists_creates_directory(self):
        """Test that ensure_library_exists creates the library directory"""
        # Remove the temp directory to test creation
        shutil.rmtree(self.temp_dir)
        assert not self.temp_dir.exists()

        self.file_service.ensure_library_exists()

        assert self.temp_dir.exists()
        assert self.temp_dir.is_dir()

    def test_ensure_library_exists_already_exists(self):
        """Test ensure_library_exists when directory already exists"""
        # Directory already exists from setup
        assert self.temp_dir.exists()

        # Should not raise an error
        self.file_service.ensure_library_exists()

        assert self.temp_dir.exists()
        assert self.temp_dir.is_dir()

    @patch("pathlib.Path.mkdir")
    def test_ensure_library_exists_error(self, mock_mkdir):
        """Test ensure_library_exists handles creation errors"""
        mock_mkdir.side_effect = OSError("Permission denied")

        with pytest.raises(ServiceError, match="Failed to create library directory"):
            self.file_service.ensure_library_exists()

    def test_get_song_directory_creates_directory(self):
        """Test get_song_directory creates song directory"""
        song_id = "test-song-123"

        result = self.file_service.get_song_directory(song_id)

        expected_path = self.temp_dir / song_id
        assert result == expected_path
        assert result.exists()
        assert result.is_dir()

    def test_get_song_directory_already_exists(self):
        """Test get_song_directory when directory already exists"""
        song_id = "test-song-123"
        song_dir = self.temp_dir / song_id
        song_dir.mkdir(parents=True, exist_ok=True)

        result = self.file_service.get_song_directory(song_id)

        assert result == song_dir
        assert result.exists()
        assert result.is_dir()

    @patch("pathlib.Path.mkdir")
    def test_get_song_directory_error(self, mock_mkdir):
        """Test get_song_directory handles creation errors"""
        mock_mkdir.side_effect = OSError("Permission denied")
        song_id = "test-song-123"

        with pytest.raises(
            ServiceError, match=f"Failed to create song directory for {song_id}"
        ):
            self.file_service.get_song_directory(song_id)

    def test_get_vocals_path_default_extension(self):
        """Test get_vocals_path with default extension"""
        song_id = "test-song-123"

        result = self.file_service.get_vocals_path(song_id)

        expected_path = self.temp_dir / song_id / "vocals.wav"
        assert result == expected_path

    def test_get_vocals_path_custom_extension(self):
        """Test get_vocals_path with custom extension"""
        song_id = "test-song-123"
        extension = ".mp3"

        result = self.file_service.get_vocals_path(song_id, extension)

        expected_path = self.temp_dir / song_id / "vocals.mp3"
        assert result == expected_path

    def test_get_instrumental_path_default_extension(self):
        """Test get_instrumental_path with default extension"""
        song_id = "test-song-123"

        result = self.file_service.get_instrumental_path(song_id)

        expected_path = self.temp_dir / song_id / "instrumental.wav"
        assert result == expected_path

    def test_get_instrumental_path_custom_extension(self):
        """Test get_instrumental_path with custom extension"""
        song_id = "test-song-123"
        extension = ".flac"

        result = self.file_service.get_instrumental_path(song_id, extension)

        expected_path = self.temp_dir / song_id / "instrumental.flac"
        assert result == expected_path

    @patch("app.services.file_service.get_config")
    def test_get_original_path_default_extension(self, mock_get_config):
        """Test get_original_path with default extension"""
        mock_config = Mock()
        mock_config.ORIGINAL_FILENAME_SUFFIX = "_original"
        mock_get_config.return_value = mock_config

        song_id = "test-song-123"

        result = self.file_service.get_original_path(song_id)

        expected_path = self.temp_dir / song_id / "test-song-123_original.mp3"
        assert result == expected_path

    @patch("app.services.file_service.get_config")
    def test_get_original_path_custom_extension(self, mock_get_config):
        """Test get_original_path with custom extension"""
        mock_config = Mock()
        mock_config.ORIGINAL_FILENAME_SUFFIX = "_original"
        mock_get_config.return_value = mock_config

        song_id = "test-song-123"
        extension = ".wav"

        result = self.file_service.get_original_path(song_id, extension)

        expected_path = self.temp_dir / song_id / "test-song-123_original.wav"
        assert result == expected_path

    def test_get_thumbnail_path(self):
        """Test get_thumbnail_path"""
        song_id = "test-song-123"

        result = self.file_service.get_thumbnail_path(song_id)

        expected_path = self.temp_dir / song_id / "thumbnail.jpg"
        assert result == expected_path

    def test_get_cover_art_path(self):
        """Test get_cover_art_path"""
        song_id = "test-song-123"

        result = self.file_service.get_cover_art_path(song_id)

        expected_path = self.temp_dir / song_id / "cover.jpg"
        assert result == expected_path

    def test_delete_song_files_success(self):
        """Test successful deletion of song files"""
        song_id = "test-song-123"
        song_dir = self.temp_dir / song_id
        song_dir.mkdir(parents=True, exist_ok=True)

        # Create some test files
        (song_dir / "vocals.wav").touch()
        (song_dir / "instrumental.wav").touch()
        (song_dir / "metadata.json").touch()

        assert song_dir.exists()

        result = self.file_service.delete_song_files(song_id)

        assert result is True
        assert not song_dir.exists()

    def test_delete_song_files_directory_not_exists(self):
        """Test deletion when directory doesn't exist"""
        song_id = "nonexistent-song"

        result = self.file_service.delete_song_files(song_id)

        assert result is False

    @patch("shutil.rmtree")
    def test_delete_song_files_error(self, mock_rmtree):
        """Test delete_song_files handles deletion errors"""
        mock_rmtree.side_effect = OSError("Permission denied")
        song_id = "test-song-123"
        song_dir = self.temp_dir / song_id
        song_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(
            ServiceError, match=f"Failed to delete files for song {song_id}"
        ):
            self.file_service.delete_song_files(song_id)

    def test_get_processed_song_ids_with_songs(self):
        """Test get_processed_song_ids with existing song directories"""
        # Create test song directories
        song_ids = ["song-1", "song-2", "song-3"]
        for song_id in song_ids:
            (self.temp_dir / song_id).mkdir(parents=True, exist_ok=True)

        # Create a regular file (should be ignored)
        (self.temp_dir / "not-a-song.txt").touch()

        # Create a hidden directory (should be ignored)
        (self.temp_dir / ".hidden").mkdir(parents=True, exist_ok=True)

        result = self.file_service.get_processed_song_ids()

        assert len(result) == 3
        assert set(result) == set(song_ids)

    def test_get_processed_song_ids_empty_library(self):
        """Test get_processed_song_ids with empty library"""
        result = self.file_service.get_processed_song_ids()

        assert result == []

    def test_get_processed_song_ids_library_not_exists(self):
        """Test get_processed_song_ids when library doesn't exist"""
        # Remove the temp directory
        shutil.rmtree(self.temp_dir)

        result = self.file_service.get_processed_song_ids()

        assert result == []

    @patch("pathlib.Path.iterdir")
    def test_get_processed_song_ids_error(self, mock_iterdir):
        """Test get_processed_song_ids handles scanning errors"""
        mock_iterdir.side_effect = OSError("Permission denied")

        with pytest.raises(ServiceError, match="Failed to scan library directory"):
            self.file_service.get_processed_song_ids()

    def test_song_directory_exists_true(self):
        """Test song_directory_exists returns True when directory exists"""
        song_id = "test-song-123"
        song_dir = self.temp_dir / song_id
        song_dir.mkdir(parents=True, exist_ok=True)

        result = self.file_service.song_directory_exists(song_id)

        assert result is True

    def test_song_directory_exists_false(self):
        """Test song_directory_exists returns False when directory doesn't exist"""
        song_id = "nonexistent-song"

        result = self.file_service.song_directory_exists(song_id)

        assert result is False

    def test_song_directory_exists_file_not_directory(self):
        """Test song_directory_exists returns False when path is a file"""
        song_id = "test-song-123"
        file_path = self.temp_dir / song_id
        file_path.touch()  # Create a file, not directory

        result = self.file_service.song_directory_exists(song_id)

        assert result is False

    def test_get_file_size_existing_file(self):
        """Test get_file_size for existing file"""
        test_file = self.temp_dir / "test_file.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content)

        result = self.file_service.get_file_size(test_file)

        assert result == len(test_content.encode("utf-8"))

    def test_get_file_size_nonexistent_file(self):
        """Test get_file_size for nonexistent file"""
        test_file = self.temp_dir / "nonexistent.txt"

        result = self.file_service.get_file_size(test_file)

        assert result is None

    def test_get_file_size_directory(self):
        """Test get_file_size for directory"""
        test_dir = self.temp_dir / "test_dir"
        test_dir.mkdir()

        result = self.file_service.get_file_size(test_dir)

        assert result is None

    @patch("pathlib.Path.stat")
    def test_get_file_size_error(self, mock_stat):
        """Test get_file_size handles stat errors"""
        mock_stat.side_effect = OSError("Permission denied")
        test_file = self.temp_dir / "test_file.txt"
        test_file.touch()

        result = self.file_service.get_file_size(test_file)

        assert result is None

    def test_list_song_files_with_files(self):
        """Test list_song_files with existing files"""
        song_id = "test-song-123"
        song_dir = self.temp_dir / song_id
        song_dir.mkdir(parents=True, exist_ok=True)

        # Create test files
        files = ["vocals.wav", "instrumental.wav", "metadata.json", "cover.jpg"]
        for filename in files:
            (song_dir / filename).touch()

        # Create a subdirectory (should be ignored)
        (song_dir / "subdir").mkdir()

        result = self.file_service.list_song_files(song_id)

        assert len(result) == 4
        result_names = [f.name for f in result]
        assert set(result_names) == set(files)

    def test_list_song_files_empty_directory(self):
        """Test list_song_files with empty directory"""
        song_id = "test-song-123"
        song_dir = self.temp_dir / song_id
        song_dir.mkdir(parents=True, exist_ok=True)

        result = self.file_service.list_song_files(song_id)

        assert result == []

    def test_list_song_files_directory_not_exists(self):
        """Test list_song_files when directory doesn't exist"""
        song_id = "nonexistent-song"

        result = self.file_service.list_song_files(song_id)

        assert result == []

    @patch("pathlib.Path.iterdir")
    def test_list_song_files_error(self, mock_iterdir):
        """Test list_song_files handles scanning errors"""
        mock_iterdir.side_effect = OSError("Permission denied")
        song_id = "test-song-123"
        song_dir = self.temp_dir / song_id
        song_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(
            ServiceError, match=f"Failed to list files for song {song_id}"
        ):
            self.file_service.list_song_files(song_id)


class TestFileServiceIntegration:
    """Integration tests for FileService with real file system operations"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.file_service = FileService(base_library_dir=self.temp_dir)

    def teardown_method(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_full_song_workflow(self):
        """Test a complete workflow with a song"""
        song_id = "integration-test-song"

        # 1. Check song directory doesn't exist initially
        assert not self.file_service.song_directory_exists(song_id)

        # 2. Get song directory (should create it)
        song_dir = self.file_service.get_song_directory(song_id)
        assert song_dir.exists()
        assert self.file_service.song_directory_exists(song_id)

        # 3. Get various file paths
        vocals_path = self.file_service.get_vocals_path(song_id)
        instrumental_path = self.file_service.get_instrumental_path(song_id)
        thumbnail_path = self.file_service.get_thumbnail_path(song_id)

        # 4. Create some test files
        vocals_path.write_text("vocals content")
        instrumental_path.write_text("instrumental content")
        thumbnail_path.write_bytes(b"thumbnail data")

        # 5. List files
        files = self.file_service.list_song_files(song_id)
        assert len(files) == 3
        file_names = {f.name for f in files}
        assert file_names == {"vocals.wav", "instrumental.wav", "thumbnail.jpg"}

        # 6. Check file sizes
        vocals_size = self.file_service.get_file_size(vocals_path)
        assert vocals_size == len("vocals content".encode("utf-8"))

        # 7. Check processed song IDs
        processed_ids = self.file_service.get_processed_song_ids()
        assert song_id in processed_ids

        # 8. Delete song files
        result = self.file_service.delete_song_files(song_id)
        assert result is True
        assert not self.file_service.song_directory_exists(song_id)
        assert not song_dir.exists()

    def test_multiple_songs_workflow(self):
        """Test workflow with multiple songs"""
        song_ids = ["song-1", "song-2", "song-3"]

        # Create directories for all songs
        for song_id in song_ids:
            song_dir = self.file_service.get_song_directory(song_id)
            # Create a file in each directory
            (song_dir / "test.txt").touch()

        # Check all songs are processed
        processed_ids = self.file_service.get_processed_song_ids()
        assert set(processed_ids) == set(song_ids)

        # Delete one song
        self.file_service.delete_song_files("song-2")

        # Check remaining songs
        processed_ids = self.file_service.get_processed_song_ids()
        assert set(processed_ids) == {"song-1", "song-3"}

        # Clean up remaining songs
        for song_id in ["song-1", "song-3"]:
            self.file_service.delete_song_files(song_id)

        # Check all songs are deleted
        processed_ids = self.file_service.get_processed_song_ids()
        assert processed_ids == []


if __name__ == "__main__":
    pytest.main([__file__])
