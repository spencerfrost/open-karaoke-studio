# Song Data Access & Business Logic

Open Karaoke Studio now uses a repository pattern for all song-related operations. The legacy service layer and `song_operations` module have been fully removed. All song CRUD, search, and metadata operations are performed directly via the `SongRepository` class, which provides a clean, testable interface to the database.

## Overview

- **No more service layer:** Controllers and scripts interact directly with the repository.
- **No more song_operations:** All legacy functions are gone; use repository methods instead.
- **Consistent API:** All song data access is through `SongRepository`, ensuring maintainability and testability.

## Repository Pattern

The `SongRepository` class provides all CRUD and query operations for songs:

```python
from app.repositories.song_repository import SongRepository
from app.db.database import get_db_session

with get_db_session() as session:
    repo = SongRepository(session)
    # Fetch all songs
    songs = repo.fetch_all()
    # Fetch a single song
    song = repo.fetch(song_id)
    # Create a song
    new_song = repo.create(song_data)
    # Update a song
    updated_song = repo.update(song_id, **fields)
    # Delete a song
    repo.delete(song_id)
```

## API Integration Example

API controllers now use the repository directly:

```python
@song_bp.route('', methods=['GET'])
def get_songs():
    with get_db_session() as session:
        repo = SongRepository(session)
        songs = repo.fetch_all()
        response_data = [song.to_dict() for song in songs]
    return jsonify(response_data)
```

## Key Features

- **Direct DB access:** No intermediate service layer; business logic is in the controller or repository as needed.
- **Testable:** Repository can be mocked or used with a test database for unit/integration tests.
- **Consistent error handling:** All exceptions are handled at the controller level, using custom error classes as needed.
- **Data transformation:** Use `.to_dict()` on models for API responses.

## Testing

- **Unit tests:** Test repository methods directly or mock them in controller tests.
- **Integration tests:** Use a test database to verify end-to-end behavior.

## Future Enhancements

- **Advanced search:** Extend repository with more query methods as needed.
- **Async support:** Consider async DB access for performance.
- **Batch operations:** Add batch methods for efficiency if required.

## Related Services

- [File Service](./file-service.md) — Handles file system operations
- [Metadata Service](./metadata-service.md) — Manages song metadata
- [Sync Service](./sync-service.md) — Coordinates database/filesystem synchronization
- [YouTube Service](./youtube-service.md) — Handles YouTube integration

---

**Implementation Status:** ✅ Repository pattern fully adopted
**Location:** `backend/app/repositories/song_repository.py`
**API Integration:** `backend/app/api/songs.py`
