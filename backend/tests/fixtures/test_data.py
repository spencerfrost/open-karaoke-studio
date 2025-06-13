"""
Test data fixtures and factories for Open Karaoke Studio backend tests.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path

# We'll import these when they're available
try:
    from app.db.models import DbSong, DbJob, Song, SongMetadata, JobStatus, Job
except ImportError:
    # For when running tests without app context
    DbSong = None
    DbJob = None
    Song = None
    SongMetadata = None
    JobStatus = None
    Job = None


def create_test_db_song(data: Optional[Dict[str, Any]] = None) -> 'DbSong':
    """Create a test DbSong with default or provided data"""
    default_data = {
        "id": "test-song-123",
        "title": "Test Song",
        "artist": "Test Artist", 
        "duration": 180,
        "favorite": False,
        "date_added": datetime.now(timezone.utc),
        "source": "upload"
    }
    
    if data:
        default_data.update(data)
    
    if DbSong:
        return DbSong(**default_data)
    else:
        # Return a mock object for when models aren't available
        from unittest.mock import Mock
        mock_song = Mock()
        for key, value in default_data.items():
            setattr(mock_song, key, value)
        return mock_song


def create_test_song(data: Optional[Dict[str, Any]] = None) -> 'Song':
    """Create a test Song Pydantic model"""
    default_data = {
        "id": "test-song-123",
        "title": "Test Song",
        "artist": "Test Artist",
        "duration": 180,
        "status": "processed",
        "favorite": False,
        "dateAdded": datetime.now(timezone.utc).isoformat(),
        "source": "upload"
    }
    
    if data:
        default_data.update(data)
    
    if Song:
        return Song(**default_data)
    else:
        # Return a mock object for when models aren't available
        from unittest.mock import Mock
        mock_song = Mock()
        for key, value in default_data.items():
            setattr(mock_song, key, value)
        mock_song.model_dump = lambda mode=None: default_data
        mock_song.dict = lambda: default_data
        return mock_song


def create_test_metadata(data: Optional[Dict[str, Any]] = None) -> 'SongMetadata':
    """Create test song metadata"""
    default_data = {
        "title": "Test Song",
        "artist": "Test Artist",
        "duration": 180,
        "favorite": False,
        "dateAdded": datetime.now(timezone.utc)
    }
    
    if data:
        default_data.update(data)
    
    if SongMetadata:
        return SongMetadata(**default_data)
    else:
        # Return a mock object for when models aren't available
        from unittest.mock import Mock
        mock_metadata = Mock()
        for key, value in default_data.items():
            setattr(mock_metadata, key, value)
        return mock_metadata


def create_test_db_job(data: Optional[Dict[str, Any]] = None) -> 'DbJob':
    """Create a test DbJob with default or provided data"""
    default_data = {
        "id": "test-job-123",
        "filename": "test_file.mp3",
        "status": "pending",
        "progress": 0,
        "task_id": None,
        "created_at": datetime.now(timezone.utc),
        "started_at": None,
        "completed_at": None,
        "error": None,
        "notes": None
    }
    
    if data:
        default_data.update(data)
    
    if DbJob:
        return DbJob(**default_data)
    else:
        # Return a mock object for when models aren't available
        from unittest.mock import Mock
        mock_job = Mock()
        for key, value in default_data.items():
            setattr(mock_job, key, value)
        return mock_job


def create_test_job(data: Optional[Dict[str, Any]] = None) -> 'Job':
    """Create a test Job dataclass"""
    default_data = {
        "id": "test-job-123",
        "filename": "test_file.mp3",
        "status": "pending",
        "progress": 0,
        "task_id": None,
        "created_at": datetime.now(timezone.utc),
        "started_at": None,
        "completed_at": None,
        "error": None,
        "notes": None
    }
    
    if data:
        default_data.update(data)
    
    if Job and JobStatus:
        # Convert string status to enum if needed
        if isinstance(default_data["status"], str):
            default_data["status"] = JobStatus(default_data["status"])
        return Job(**default_data)
    else:
        # Return a mock object for when models aren't available
        from unittest.mock import Mock
        mock_job = Mock()
        for key, value in default_data.items():
            setattr(mock_job, key, value)
        mock_job.to_dict = lambda: default_data
        return mock_job


# Sample test data constants
SAMPLE_SONGS = [
    {
        "id": "song-001",
        "title": "Classic Rock Song",
        "artist": "Test Band",
        "duration": 240,
        "source": "upload"
    },
    {
        "id": "song-002", 
        "title": "Pop Ballad",
        "artist": "Popular Artist",
        "duration": 200,
        "source": "youtube"
    },
    {
        "id": "song-003",
        "title": "Jazz Standard",
        "artist": "Jazz Musician",
        "duration": 180,
        "source": "upload"
    }
]

SAMPLE_JOBS = [
    {
        "id": "job-001",
        "filename": "rock_song.mp3",
        "status": "completed",
        "progress": 100
    },
    {
        "id": "job-002",
        "filename": "pop_ballad.mp3", 
        "status": "processing",
        "progress": 65
    },
    {
        "id": "job-003",
        "filename": "jazz_standard.mp3",
        "status": "pending",
        "progress": 0
    }
]


def create_sample_audio_file(temp_dir: Path, filename: str = "test_audio.mp3") -> Path:
    """Create a sample audio file for testing"""
    audio_file = temp_dir / filename
    # Create a minimal MP3-like file (just for testing file operations)
    audio_file.write_bytes(b'\x49\x44\x33\x03\x00\x00\x00')  # Basic MP3 header
    return audio_file


def create_sample_song_directory(temp_dir: Path, song_id: str = "test-song") -> Path:
    """Create a sample song directory structure for testing"""
    song_dir = temp_dir / song_id
    song_dir.mkdir(exist_ok=True)
    
    # Create sample files
    (song_dir / "original.mp3").write_bytes(b'\x49\x44\x33\x03\x00\x00\x00')
    (song_dir / "vocals.mp3").write_bytes(b'\x49\x44\x33\x03\x00\x00\x00')
    (song_dir / "instrumental.mp3").write_bytes(b'\x49\x44\x33\x03\x00\x00\x00')
    (song_dir / "metadata.json").write_text('{"title": "Test Song", "artist": "Test Artist"}')
    
    return song_dir
