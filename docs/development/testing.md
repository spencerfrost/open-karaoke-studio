# Testing Infrastructure

## Overview

Open Karaoke Studio has a comprehensive testing infrastructure that ensures code quality and reliability across all backend components. The testing system includes unit tests, integration tests, fixtures, utilities, and CI/CD integration.

## Testing Directory Structure

```
backend/tests/
├── conftest.py                    # Shared pytest configuration
├── pytest.ini                    # Pytest settings
├── fixtures/                     # Shared test fixtures
│   ├── __init__.py
│   ├── app_fixtures.py           # Flask app and client fixtures
│   ├── database_fixtures.py      # Database and session fixtures
│   ├── file_fixtures.py          # File system fixtures
│   └── sample_data.py            # Test data factories
├── integration/                  # Integration tests
│   ├── __init__.py
│   ├── test_api/                 # API endpoint integration tests
│   │   ├── test_songs_api.py
│   │   ├── test_youtube_api.py
│   │   ├── test_lyrics_api.py
│   │   └── test_jobs_api.py
│   ├── test_celery/              # Celery task integration tests
│   │   ├── test_audio_processing.py
│   │   └── test_job_management.py
│   └── test_database/            # Database integration tests
│       ├── test_song_operations.py
│       └── test_migrations.py
├── unit/                         # Unit tests
│   ├── __init__.py
│   ├── test_api/                 # API layer unit tests
│   │   ├── test_decorators.py
│   │   ├── test_responses.py
│   │   └── test_metadata_endpoints.py
│   ├── test_services/            # Service layer unit tests
│   │   ├── test_audio_service.py
│   │   ├── test_file_service.py
│   │   ├── test_song_service.py
│   │   ├── test_lyrics_service.py
│   │   └── youtube_service/      # Comprehensive YouTube service tests
│   │       ├── __init__.py
│   │       ├── test_core_functionality.py
│   │       ├── test_error_handling.py
│   │       ├── test_edge_cases.py
│   │       └── test_integration.py
│   ├── test_db/                  # Database layer unit tests
│   │   ├── test_models.py
│   │   ├── test_song_operations.py
│   │   └── test_database_utils.py
│   └── test_config/              # Configuration tests
│       ├── test_base_config.py
│       ├── test_environment_loading.py
│       └── test_logging_config.py
└── utils/                        # Test utilities
    ├── __init__.py
    ├── api_utils.py              # API testing utilities
    ├── database_utils.py         # Database testing utilities
    ├── file_utils.py             # File system testing utilities
    └── mock_factories.py         # Mock object factories
```

## Pytest Configuration

### Core Configuration (`pytest.ini`)

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --verbose
    --tb=short
    --strict-markers
    --disable-warnings
    -ra
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    api: marks tests as API tests
    database: marks tests as database tests
    celery: marks tests as Celery task tests
```

### Shared Configuration (`conftest.py`)

```python
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock
from flask import Flask

from app import create_app
from app.config.testing import TestingConfig
from app.db.database import get_db_session, engine
from app.db.models import Base

@pytest.fixture(scope="session")
def app():
    """Create test Flask app"""
    app = create_app(TestingConfig)

    with app.app_context():
        # Create test database
        Base.metadata.create_all(bind=engine)
        yield app
        # Cleanup
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def db_session(app):
    """Create database session for tests"""
    with get_db_session() as session:
        yield session
```

## Testing Categories

### Unit Tests

#### Service Layer Testing

```python
# tests/unit/test_services/test_song_service.py
import pytest
from unittest.mock import Mock, patch
from app.services.song_service import SongService
from app.exceptions import ServiceError, NotFoundError

class TestSongService:
    """Unit tests for SongService"""

    @pytest.fixture
    def song_service(self):
        return SongService()

    def test_get_all_songs_success(self, song_service, mock_db_songs):
        """Test successful retrieval of all songs"""
        with patch('app.db.song_operations.get_all_songs', return_value=mock_db_songs):
            songs = song_service.get_all_songs()

            assert len(songs) == 2
            assert all(hasattr(song, 'id') for song in songs)

    def test_get_song_by_id_not_found(self, song_service):
        """Test get_song_by_id with non-existent song"""
        with patch('app.db.song_operations.get_song', return_value=None):
            result = song_service.get_song_by_id("nonexistent")

            assert result is None

    def test_delete_song_with_cleanup(self, song_service):
        """Test song deletion with file cleanup"""
        with patch('app.db.song_operations.delete_song', return_value=True):
            with patch('app.services.FileService.delete_song_files', return_value=True):
                result = song_service.delete_song("test-song-123")

                assert result is True
```

#### Advanced Error Handling Testing

```python
# tests/unit/test_services/youtube_service/test_error_handling.py
class TestAdvancedErrorHandling:
    """Test advanced error handling scenarios in YouTube Service"""

    def test_network_error_user_friendly_message(self, youtube_service):
        """Test that network errors produce user-friendly messages"""
        with patch('app.services.youtube_service.yt_dlp.YoutubeDL') as mock_ytdl:
            mock_ydl_instance = Mock()
            mock_ytdl.return_value.__enter__.return_value = mock_ydl_instance
            mock_ydl_instance.extract_info.side_effect = Exception("HTTP Error 403: Forbidden")

            with pytest.raises(ServiceError) as exc_info:
                youtube_service.download_video("dQw4w9WgXcQ")

            assert "Failed to download YouTube video" in str(exc_info.value)

    def test_partial_failure_download_succeeds_task_queue_fails(self, youtube_service):
        """Test partial failure: Download succeeds but task queue fails"""
        with pytest.raises(ServiceError, match="Failed to queue YouTube processing.*song_id is required"):
            youtube_service.download_and_process_async("dQw4w9WgXcQ")
```

### Integration Tests

#### API Endpoint Testing

```python
# tests/integration/test_api/test_songs_api.py
class TestSongsAPI:
    """Integration tests for Songs API endpoints"""

    def test_get_songs_endpoint(self, client, sample_songs):
        """Test GET /api/songs endpoint"""
        response = client.get('/api/songs')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 0

    @patch('app.api.songs.SongService')
    def test_delete_song_success(self, mock_song_service_class, client):
        """Test DELETE /api/songs/<id> endpoint success"""
        mock_service = Mock()
        mock_song_service_class.return_value = mock_service
        mock_service.delete_song.return_value = True

        response = client.delete('/api/songs/test-song-123')

        assert response.status_code == 200
        mock_service.delete_song.assert_called_once_with("test-song-123")

class TestSongsAPIErrorHandling:
    """Test error handling in songs API"""

    def test_internal_server_error_handling(self, client):
        """Test that internal server errors are handled gracefully"""
        with patch('app.db.database.get_all_songs', side_effect=Exception("Unexpected error")):
            response = client.get('/api/songs')

            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data
```

#### Celery Task Testing

```python
# tests/integration/test_celery/test_audio_processing.py
class TestAudioProcessingTasks:
    """Integration tests for Celery audio processing tasks"""

    def test_process_audio_job_success(self, sample_job, temp_audio_file):
        """Test successful audio processing job"""
        from app.jobs.jobs import process_audio_job

        # Create test job
        job_id = sample_job.id

        # Run task synchronously for testing
        result = process_audio_job.apply(args=[job_id])

        assert result.successful()
        assert result.result == "completed"

    def test_process_audio_job_file_not_found(self):
        """Test audio processing with missing file"""
        from app.jobs.jobs import process_audio_job

        result = process_audio_job.apply(args=["nonexistent-job"])

        assert result.failed()
        assert "Job not found" in str(result.result)
```

## Test Fixtures and Utilities

### Database Fixtures

```python
# tests/fixtures/database_fixtures.py
@pytest.fixture
def clean_database(app):
    """Provide clean database for each test"""
    with app.app_context():
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        yield
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def sample_songs(db_session):
    """Create sample songs for testing"""
    from tests.utils.mock_factories import create_mock_song

    songs = []
    for i in range(3):
        song = create_mock_song(
            id=f"test-song-{i}",
            title=f"Test Song {i}",
            artist=f"Test Artist {i}"
        )
        db_session.add(song)
        songs.append(song)

    db_session.commit()
    return songs
```

### File System Fixtures

```python
# tests/fixtures/file_fixtures.py
@pytest.fixture
def temp_directory():
    """Create temporary directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_song_directory(temp_directory):
    """Create mock song directory structure"""
    song_id = "test-song-123"
    song_dir = temp_directory / song_id
    song_dir.mkdir()

    # Create mock audio files
    (song_dir / "original.mp3").touch()
    (song_dir / "vocals.mp3").touch()
    (song_dir / "instrumental.mp3").touch()

    return song_dir
```

### Mock Factories

```python
# tests/utils/mock_factories.py
from unittest.mock import Mock
from app.db.models import DbSong
from app.schemas.song import Song

def create_mock_song(
    id: str = "test-song-123",
    title: str = "Test Song",
    artist: str = "Test Artist",
    **kwargs
) -> DbSong:
    """Create mock DbSong for testing"""
    return DbSong(
        id=id,
        title=title,
        artist=artist,
        album=kwargs.get('album', 'Test Album'),
        duration=kwargs.get('duration', 180),
        date_added=kwargs.get('date_added', datetime.utcnow()),
        **kwargs
    )

def create_mock_metadata(**kwargs) -> dict:
    """Create mock metadata dictionary for testing (SongMetadata class was removed)"""
    return {
        'title': kwargs.get('title', 'Test Song'),
        'artist': kwargs.get('artist', 'Test Artist'),
        'album': kwargs.get('album', 'Test Album'),
        'duration': kwargs.get('duration', 180),
        **kwargs
    }

def create_mock_song_api(**kwargs) -> Song:
    """Create mock Song for API testing"""
    return Song(
        id=kwargs.get('id', 'test-song-123'),
        title=kwargs.get('title', 'Test Song'),
        artist=kwargs.get('artist', 'Test Artist'),
        album=kwargs.get('album', 'Test Album'),
        duration=kwargs.get('duration', 180),
        **kwargs
    )
```

## Test Utilities

### API Testing Utilities

```python
# tests/utils/api_utils.py
def assert_successful_response(response_data: Dict[str, Any]):
    """Assert that response indicates success"""
    assert 'success' in response_data
    assert response_data['success'] is True

def assert_error_response(response_data: Dict[str, Any], expected_error_message: str = None):
    """Assert that response indicates an error"""
    assert 'error' in response_data or ('success' in response_data and not response_data['success'])

    if expected_error_message:
        error_msg = response_data.get('error', {}).get('message', response_data.get('error', ''))
        assert expected_error_message.lower() in str(error_msg).lower()
```

### Database Testing Utilities

```python
# tests/utils/database_utils.py
def create_test_song_in_db(db_session, **kwargs):
    """Helper to create test song in database"""
    song = create_mock_song(**kwargs)
    db_session.add(song)
    db_session.commit()
    db_session.refresh(song)
    return song

def assert_song_exists_in_db(db_session, song_id: str):
    """Assert that song exists in database"""
    song = db_session.query(DbSong).filter(DbSong.id == song_id).first()
    assert song is not None
    return song
```

## Running Tests

### Command Line Usage

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit                    # Unit tests only
pytest -m integration             # Integration tests only
pytest -m "not slow"              # Skip slow tests

# Run specific test files
pytest tests/unit/test_services/test_song_service.py
pytest tests/integration/test_api/

# Run with coverage
pytest --cov=app --cov-report=html

# Run tests in parallel
pytest -n auto                    # Auto-detect CPU cores
pytest -n 4                       # Use 4 processes
```

### Test Selection

```bash
# Run tests by pattern
pytest -k "test_song"             # All tests with 'song' in name
pytest -k "not test_integration"  # Exclude integration tests

# Run failed tests from last run
pytest --lf                       # Last failed
pytest --ff                       # Failed first
```

## Coverage Reporting

### Configuration

```ini
# .coveragerc
[run]
source = app
omit =
    */tests/*
    */venv/*
    */migrations/*
    */conftest.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
```

### Coverage Targets

- **Overall Coverage**: >85%
- **Service Layer**: >90%
- **API Layer**: >80%
- **Database Operations**: >85%
- **Critical Paths**: 100%

## CI/CD Integration

### GitHub Actions Configuration

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.9

      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install -r backend/requirements-test.txt

      - name: Run tests
        run: |
          cd backend
          pytest --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

### Test Environment Variables

```bash
# Test-specific environment variables
FLASK_ENV=testing
DATABASE_URL=sqlite:///:memory:
CELERY_ALWAYS_EAGER=True
TESTING=True
```

## Best Practices

### Test Organization

1. **Separate unit and integration tests** clearly
2. **Use descriptive test names** that explain what is being tested
3. **Group related tests** in classes
4. **Follow AAA pattern** (Arrange, Act, Assert)
5. **Keep tests independent** and idempotent

### Test Data Management

1. **Use factories** for test data creation
2. **Clean up after tests** with proper fixtures
3. **Avoid hardcoded values** in test data
4. **Use realistic test data** that represents actual usage

### Mocking Strategy

1. **Mock external dependencies** (APIs, file system, databases)
2. **Use interface mocking** for service dependencies
3. **Verify mock interactions** where appropriate
4. **Keep mocks simple** and focused

### Performance Considerations

1. **Use fast test databases** (in-memory SQLite)
2. **Minimize I/O operations** in unit tests
3. **Parallel test execution** for faster feedback
4. **Mark slow tests** appropriately

## Related Documentation

- [Development Setup](../setup/README.md)
- [Service Layer Design](../../architecture/backend/service-layer-design.md)
- [API Documentation](../../api/README.md)
- [Database Design](../../architecture/backend/database-design.md)
