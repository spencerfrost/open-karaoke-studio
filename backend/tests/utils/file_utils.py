"""
File utilities for testing.
"""

import shutil
import tempfile
from pathlib import Path
from typing import List
from unittest.mock import Mock


def create_temp_directory() -> Path:
    """Create a temporary directory for testing"""
    return Path(tempfile.mkdtemp())


def cleanup_temp_directory(temp_dir: Path):
    """Clean up temporary directory"""
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


def create_test_audio_file(directory: Path, filename: str = "test.mp3") -> Path:
    """Create a test audio file"""
    file_path = directory / filename
    # Create minimal MP3-like content for testing
    file_path.write_bytes(b"\x49\x44\x33\x03\x00\x00\x00\x00\x00\x00")
    return file_path


def create_test_song_structure(base_dir: Path, song_id: str) -> Path:
    """Create a complete test song directory structure"""
    song_dir = base_dir / song_id
    song_dir.mkdir(exist_ok=True)

    # Create audio files
    create_test_audio_file(song_dir, "original.mp3")
    create_test_audio_file(song_dir, "vocals.mp3")
    create_test_audio_file(song_dir, "instrumental.mp3")

    # Create metadata file
    metadata = {
        "title": "Test Song",
        "artist": "Test Artist",
        "duration": 180,
    }

    import json

    (song_dir / "metadata.json").write_text(json.dumps(metadata))

    return song_dir


def assert_file_exists(file_path: Path):
    """Assert that a file exists"""
    assert file_path.exists(), f"File {file_path} does not exist"


def assert_directory_exists(dir_path: Path):
    """Assert that a directory exists"""
    assert dir_path.exists(), f"Directory {dir_path} does not exist"
    assert dir_path.is_dir(), f"Path {dir_path} is not a directory"


def assert_file_contains(file_path: Path, expected_content: str):
    """Assert that a file contains expected content"""
    assert_file_exists(file_path)
    content = file_path.read_text()
    assert (
        expected_content in content
    ), f"File {file_path} does not contain '{expected_content}'"


def mock_file_operations():
    """Create mocks for common file operations"""
    mocks = Mock()
    mocks.exists = Mock(return_value=True)
    mocks.is_file = Mock(return_value=True)
    mocks.is_dir = Mock(return_value=True)
    mocks.mkdir = Mock()
    mocks.write_text = Mock()
    mocks.read_text = Mock(return_value='{"test": "data"}')
    mocks.write_bytes = Mock()
    mocks.read_bytes = Mock(return_value=b"test data")
    return mocks


class MockPath:
    """Mock pathlib.Path for testing"""

    def __init__(self, path_str: str):
        self.path_str = path_str
        self._exists = True
        self._is_file = True
        self._is_dir = False

    def __str__(self):
        return self.path_str

    def __truediv__(self, other):
        return MockPath(f"{self.path_str}/{other}")

    def exists(self):
        return self._exists

    def is_file(self):
        return self._is_file

    def is_dir(self):
        return self._is_dir

    def mkdir(self, exist_ok=False):
        pass

    def write_text(self, content):
        pass

    def read_text(self):
        return '{"test": "data"}'

    def write_bytes(self, content):
        pass

    def read_bytes(self):
        return b"test data"

    @property
    def name(self):
        return self.path_str.split("/")[-1]

    @property
    def parent(self):
        parent_path = "/".join(self.path_str.split("/")[:-1])
        return MockPath(parent_path)

    def resolve(self):
        return self
