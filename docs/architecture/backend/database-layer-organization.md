# Database Layer Organization

## Overview

The Open Karaoke Studio backend uses a clean separation between database infrastructure and business logic operations, organized for maintainability and future scalability.

## Directory Structure

```
backend/app/db/
├── __init__.py              # Public exports and session management
├── database.py              # Database infrastructure (~165 lines)
├── song_operations.py       # Song business logic (~541 lines)
├── models/                  # SQLAlchemy model definitions
│   ├── __init__.py
│   ├── base.py
│   ├── job.py
│   ├── karaoke_queue.py
│   ├── song.py
│   └── user.py
├── job_store/              # Job persistence functionality
└── migrate.py              # Database migration utilities
```

## Architecture Principles

### Separation of Concerns

The database layer is organized around two main responsibilities:

1. **Infrastructure (`database.py`)**: Database connections, sessions, schema management
2. **Business Logic (`song_operations.py`)**: Domain-specific operations and queries

### Why This Organization?

**Songs-Centric Design**: In a karaoke application, songs are the core entity. Other concepts like "artists" and "search" are really just different ways of querying and organizing songs:

- **Artists**: VARCHAR field in songs table, not separate entities
- **Artist operations**: Song queries filtered/grouped by artist
- **Search operations**: Song queries with text matching
- **Everything revolves around songs**: Core entity with derived operations

This natural domain structure makes a single `song_operations.py` file more logical than artificial separation.

## Database Infrastructure (`database.py`)

### Core Responsibilities

```python
# Database engine and connection management
engine = create_engine(DATABASE_URL, **connection_options)
SessionLocal = sessionmaker(bind=engine)

# Session context manager
@contextmanager
def get_db_session() -> Iterator[Session]:
    """Provides database session with automatic cleanup"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

### Features

- **SQLite Optimization**: Cross-process reliability, connection pooling
- **Session Management**: Context managers for automatic cleanup
- **Schema Management**: Database initialization and updates
- **Connection Configuration**: Timeout handling, pre-ping validation

### Database Configuration

```python
# SQLite-specific optimizations
if DATABASE_URL.startswith('sqlite:'):
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "timeout": 30,              # 30 second lock timeout
            "check_same_thread": False  # Cross-thread access
        },
        pool_pre_ping=True,   # Verify connections
        pool_recycle=3600     # Recycle hourly
    )
```

## Song Operations (`song_operations.py`)

### Core Business Logic

The song operations module contains all song-related business logic:

#### CRUD Operations

```python
def get_songs() -> List[DbSong]
def get_song(song_id: str) -> Optional[DbSong]
def create_or_update_song(song_id: str, title: str, artist: str, **kwargs) -> Optional[DbSong]
def delete_song(song_id: str) -> bool
```

#### Query Operations

```python
def get_artists_with_counts() -> List[Tuple[str, int]]
def get_songs_by_artist(artist: str) -> List[DbSong]
def search_songs_paginated(query: str, limit: int, offset: int) -> Tuple[List[DbSong], int]
```

#### File System Integration

```python
def sync_songs_with_filesystem() -> int
def update_song_audio_paths(song_id: str, paths: Dict[str, str]) -> bool
```

#### Metadata Management

```python
def update_song_with_metadata(song_id: str, metadata: Dict[str, Any]) -> Optional[DbSong]
def get_song_as_dict(song_id: str) -> Optional[Dict[str, Any]]
```

## Session Management Patterns

### Context Manager Usage

```python
# Recommended pattern for database operations
def get_songs() -> List[DbSong]:
    try:
        with get_db_session() as session:
            songs = session.query(DbSong).order_by(DbSong.date_added.desc()).all()
            return songs
    except Exception as e:
        logging.error(f"Error getting songs: {e}")
        return []
```

### Transaction Handling

```python
def create_or_update_song(song_id: str, title: str, artist: str, **kwargs) -> Optional[DbSong]:
    try:
        with get_db_session() as session:
            # Check for existing song
            existing_song = session.query(DbSong).filter(DbSong.id == song_id).first()

            if existing_song:
                # Update existing - direct field assignment
                existing_song.title = title
                existing_song.artist = artist
                for key, value in kwargs.items():
                    if hasattr(existing_song, key):
                        setattr(existing_song, key, value)
                song = existing_song
            else:
                # Create new
                song = DbSong(id=song_id, title=title, artist=artist, **kwargs)
                session.add(song)

            session.commit()  # Automatic via context manager
            session.refresh(song)  # Reload from database
            return song

    except Exception as e:
        logging.error(f"Error creating/updating song {song_id}: {e}")
        return None
```

## Model Integration

### Pydantic Models

```python
from ..db.models import Song, DbSong

# Clean separation: DbSong (database) ↔ Song (API)
# DbSong.to_dict() provides frontend-friendly format
song_dict = db_song.to_dict()  # camelCase for frontend
api_song = Song.model_validate(song_dict)  # Pydantic validation

# Direct database operations with parameters
db_song = DbSong(id="song-123", title="Song Title", artist="Artist Name")
```

### Model Conversion

```python
# Convert between Pydantic and SQLAlchemy models
def to_api_response(db_song: DbSong) -> Song:
    return Song(
        id=db_song.id,
        title=db_song.title,
        artist=db_song.artist,
        # ... other fields
    )
```

## Error Handling

### Database Error Patterns

```python
def get_song(song_id: str) -> Optional[DbSong]:
    try:
        with get_db_session() as session:
            song = session.query(DbSong).filter(DbSong.id == song_id).first()
            return song
    except Exception as e:
        logging.error(f"Error getting song {song_id}: {e}")
        return None  # Graceful degradation
```

### Exception Handling Strategy

1. **Log errors** with context information
2. **Return None or empty lists** for graceful degradation
3. **Let context manager handle rollback** automatically
4. **Preserve exception context** for debugging

## Performance Considerations

### Query Optimization

```python
# Efficient ordering and limiting
def get_songs() -> List[DbSong]:
    with get_db_session() as session:
        return session.query(DbSong)\
                     .order_by(DbSong.date_added.desc())\
                     .all()

# Pagination support
def search_songs_paginated(query: str, limit: int, offset: int):
    with get_db_session() as session:
        base_query = session.query(DbSong)\
                           .filter(DbSong.title.contains(query))

        total_count = base_query.count()
        songs = base_query.offset(offset).limit(limit).all()

        return songs, total_count
```

### Connection Management

- **Connection pooling** for efficient resource usage
- **Pre-ping validation** to handle stale connections
- **Automatic connection recycling** every hour
- **Proper timeout handling** for locked databases

## Future Scalability

### Design for Growth

The current organization supports future expansion:

```python
# When adding users, playlists, etc.
backend/app/db/
├── database.py              # Reusable infrastructure
├── song_operations.py       # Song-specific logic
├── user_operations.py       # User-specific logic (future)
├── playlist_operations.py   # Playlist logic (future)
└── models/                  # All model definitions
```

### Extensibility Patterns

1. **Reusable Infrastructure**: All operations use same session management
2. **Consistent Patterns**: Same error handling and transaction patterns
3. **Clear Boundaries**: Separate files for separate domains
4. **Shared Models**: Common model definitions in `models/` directory

## Migration and Schema Management

### Schema Updates

```python
# In database.py
def ensure_db_schema():
    """Ensure database schema matches current models"""
    inspector = inspect(engine)

    if not inspector.has_table('songs'):
        logging.info("Creating database schema from scratch")
        Base.metadata.create_all(bind=engine)
        return

    # Handle schema migrations
    migrate_schema_if_needed(inspector)
```

### Data Migration

```python
# In migrate.py
def migrate_existing_data():
    """Migrate data from old schema to new schema"""
    with get_db_session() as session:
        # Migration logic here
        pass
```

## Best Practices

### Database Operations

1. **Always use context managers** for session management
2. **Handle exceptions gracefully** with appropriate logging
3. **Return None/empty** for missing data rather than raising
4. **Commit explicitly** or rely on context manager
5. **Refresh objects** after commits to ensure current state

### Organization Guidelines

1. **Keep infrastructure separate** from business logic
2. **Group related operations** in domain-specific modules
3. **Use consistent error handling** patterns
4. **Document complex queries** with comments
5. **Test database operations** with appropriate fixtures

## Related Documentation

- [Database Design](../../architecture/backend/database-design.md)
- [Model Definitions](../../architecture/backend/models.md)
- [Configuration Management](../reference/configuration.md)
- [Service Layer](../../architecture/backend/service-layer-design.md)
