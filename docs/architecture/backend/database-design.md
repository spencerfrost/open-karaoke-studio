# Database Design Architecture

## Overview

The database layer implements a repository pattern with consistent session management, proper migration handling, and separation of concerns between data access and business logic. It provides a clean abstraction over SQLAlchemy operations while maintaining type safety and error handling.

## Current Implementation Status

**ORM**: SQLAlchemy with declarative models
**Migration**: Custom schema management (needs Flask-Migrate)
**Pattern**: Mixed patterns - needs repository standardization
**Status**: Partially implemented, requires refactoring

## Database Models

### Core Tables

The system uses several core tables for managing songs, jobs, and user data:

```sql
-- Songs table (primary entity)
CREATE TABLE songs (
    id VARCHAR PRIMARY KEY,
    title VARCHAR NOT NULL,
    artist VARCHAR,
    album VARCHAR,
    source VARCHAR,  -- 'youtube', 'upload', 'local'
    youtube_id VARCHAR,
    file_path VARCHAR,
    vocals_path VARCHAR,
    instrumental_path VARCHAR,
    lyrics TEXT,
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Jobs table (processing tracking)
CREATE TABLE jobs (
    id VARCHAR PRIMARY KEY,
    song_id VARCHAR REFERENCES songs(id),
    status VARCHAR,  -- 'pending', 'processing', 'completed', 'failed'
    progress INTEGER DEFAULT 0,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table (future enhancement)
CREATE TABLE users (
    id VARCHAR PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    email VARCHAR UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Repository Pattern Implementation

### Base Repository

The base repository provides common CRUD operations for all entities:

```python
from typing import TypeVar, Generic, List, Optional, Type
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.db.database import get_db_session
from app.db.models import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """Base repository providing common database operations"""

    def __init__(self, model_class: Type[ModelType]):
        self.model_class = model_class

    def get_by_id(self, id: str) -> Optional[ModelType]:
        """Retrieve entity by ID"""
        with get_db_session() as session:
            return session.query(self.model_class).filter(
                self.model_class.id == id
            ).first()

    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[ModelType]:
        """Retrieve all entities with optional pagination"""
        with get_db_session() as session:
            query = session.query(self.model_class)
            if limit:
                query = query.limit(limit).offset(offset)
            return query.all()

    def create(self, **kwargs) -> ModelType:
        """Create new entity"""
        with get_db_session() as session:
            instance = self.model_class(**kwargs)
            session.add(instance)
            session.commit()
            session.refresh(instance)
            return instance

    def update(self, id: str, **kwargs) -> Optional[ModelType]:
        """Update existing entity"""
        with get_db_session() as session:
            instance = session.query(self.model_class).filter(
                self.model_class.id == id
            ).first()
            if instance:
                for key, value in kwargs.items():
                    setattr(instance, key, value)
                session.commit()
                session.refresh(instance)
            return instance

    def delete(self, id: str) -> bool:
        """Delete entity by ID"""
        with get_db_session() as session:
            instance = session.query(self.model_class).filter(
                self.model_class.id == id
            ).first()
            if instance:
                session.delete(instance)
                session.commit()
                return True
            return False
```

### Domain-Specific Repositories

Each domain entity has its own repository with specialized queries:

```python
class SongRepository(BaseRepository[DbSong]):
    """Repository for song-specific database operations"""

    def __init__(self):
        super().__init__(DbSong)

    def get_all_ordered_by_date(self) -> List[DbSong]:
        """Get all songs ordered by date added (newest first)"""
        with get_db_session() as session:
            return session.query(self.model_class).order_by(
                desc(self.model_class.date_added)
            ).all()

    def search_by_title_or_artist(self, query: str) -> List[DbSong]:
        """Search songs by title or artist"""
        with get_db_session() as session:
            search_term = f"%{query}%"
            return session.query(self.model_class).filter(
                or_(
                    self.model_class.title.ilike(search_term),
                    self.model_class.artist.ilike(search_term)
                )
            ).all()

    def get_by_source(self, source: str) -> List[DbSong]:
        """Get songs by source (youtube, upload, etc.)"""
        with get_db_session() as session:
            return session.query(self.model_class).filter(
                self.model_class.source == source
            ).all()

    def get_by_youtube_id(self, youtube_id: str) -> Optional[DbSong]:
        """Get song by YouTube video ID"""
        with get_db_session() as session:
            return session.query(self.model_class).filter(
                self.model_class.youtube_id == youtube_id
            ).first()
```

## Session Management

### Context Manager Pattern

Database sessions are managed through context managers for automatic cleanup:

```python
from contextlib import contextmanager
from typing import Iterator
from sqlalchemy.orm import Session, sessionmaker
from .database import engine

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db_session() -> Iterator[Session]:
    """Thread-safe database session context manager"""
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

### Dependency Injection

For Flask routes and services that need database access:

```python
def get_db():
    """Database dependency for Flask routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Usage in Flask routes
@app.route('/api/songs')
def get_songs():
    song_repo = SongRepository()
    songs = song_repo.get_all_ordered_by_date()
    return jsonify([song.to_dict() for song in songs])
```

## Migration Strategy

### Flask-Migrate Integration

Moving from custom schema management to proper migrations:

```python
# Add to requirements.txt
Flask-Migrate==4.0.5

# Initialize migrations (one-time setup)
flask db init

# Create migration for current schema
flask db migrate -m "Initial migration with songs and jobs tables"

# Apply migration
flask db upgrade

# Future schema changes
flask db migrate -m "Add user authentication tables"
flask db upgrade
```

### Migration File Structure

```
migrations/
├── alembic.ini
├── env.py
├── script.py.mako
└── versions/
    ├── 001_initial_schema.py
    ├── 002_add_user_tables.py
    └── 003_enhance_job_tracking.py
```

## Data Access Patterns

### Service Layer Integration

Services use repositories instead of direct database access:

```python
class SongService:
    """Service layer for song operations"""

    def __init__(self):
        self.song_repo = SongRepository()
        self.job_repo = JobRepository()

    def get_songs(self) -> List[Song]:
        """Get all songs with proper error handling"""
        try:
            db_songs = self.song_repo.get_all_ordered_by_date()
            return [Song.model_validate(song.to_dict()) for song in db_songs]
        except Exception as e:
            logger.error(f"Error retrieving songs: {e}")
            raise ServiceError("Failed to retrieve songs")

    def create_song(self, song_data: CreateSongRequest) -> Song:
        """Create new song with validation"""
        try:
            # Validate input
            if not song_data.title or not song_data.artist:
                raise ValidationError("Title and artist are required")

            # Check for duplicates
            existing = self.song_repo.get_by_youtube_id(song_data.youtube_id)
            if existing:
                raise ConflictError("Song already exists")

            # Create song
            db_song = self.song_repo.create(**song_data.dict())
            return Song.model_validate(db_song.to_dict())

        except Exception as e:
            logger.error(f"Error creating song: {e}")
            raise
```

### Transaction Management

Complex operations use explicit transaction management:

```python
def create_song_with_job(self, song_data: dict, job_data: dict) -> tuple[Song, Job]:
    """Create song and associated job in single transaction"""
    with get_db_session() as session:
        try:
            # Create song
            song = DbSong(**song_data)
            session.add(song)
            session.flush()  # Get song ID

            # Create associated job
            job_data['song_id'] = song.id
            job = DbJob(**job_data)
            session.add(job)

            # Commit both operations
            session.commit()

            return Song.model_validate(song.to_dict()), Job.model_validate(job.to_dict())

        except Exception:
            session.rollback()
            raise
```

## Connection and Performance

### Connection Pooling

SQLAlchemy engine configuration for optimal performance:

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=10,          # Maximum number of permanent connections
    max_overflow=20,       # Maximum number of overflow connections
    pool_pre_ping=True,    # Validate connections before use
    pool_recycle=3600,     # Recycle connections after 1 hour
    echo=False             # Set to True for SQL logging in development
)
```

### Query Optimization

Repositories implement efficient queries with proper indexing:

```python
def get_songs_with_jobs(self) -> List[tuple[DbSong, Optional[DbJob]]]:
    """Efficiently fetch songs with their latest jobs"""
    with get_db_session() as session:
        return session.query(DbSong, DbJob)\
            .outerjoin(DbJob, DbSong.id == DbJob.song_id)\
            .order_by(desc(DbSong.date_added))\
            .all()
```

## Error Handling

### Database Exception Mapping

The repository layer maps database exceptions to domain exceptions:

```python
def handle_db_error(func):
    """Decorator to handle database exceptions"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except IntegrityError as e:
            if 'UNIQUE constraint failed' in str(e):
                raise ConflictError("Record already exists")
            raise
        except OperationalError as e:
            logger.error(f"Database connection error: {e}")
            raise ServiceError("Database temporarily unavailable")
        except Exception as e:
            logger.error(f"Unexpected database error: {e}")
            raise ServiceError("Database operation failed")
    return wrapper
```

## Testing Strategy

### Repository Testing

Repositories are tested with an in-memory SQLite database:

```python
@pytest.fixture
def test_db():
    """Create test database"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        yield session

def test_song_repository_create(test_db):
    """Test song creation through repository"""
    repo = SongRepository()
    song_data = {
        'title': 'Test Song',
        'artist': 'Test Artist',
        'source': 'test'
    }

    song = repo.create(**song_data)
    assert song.title == 'Test Song'
    assert song.artist == 'Test Artist'
```

### Integration Testing

Integration tests verify the complete data flow:

```python
def test_song_service_with_db(test_db):
    """Test song service database integration"""
    service = SongService()

    # Create song
    song_data = CreateSongRequest(
        title='Integration Test',
        artist='Test Artist'
    )

    created_song = service.create_song(song_data)
    assert created_song.id is not None

    # Retrieve song
    retrieved_song = service.get_song(created_song.id)
    assert retrieved_song.title == song_data.title
```

## Migration from Current Implementation

### Phase 1: Repository Implementation

1. Create base repository with common operations
2. Implement song repository with domain queries
3. Update song service to use repository

### Phase 2: Session Management

1. Standardize session management across modules
2. Remove direct SQLAlchemy usage from services
3. Implement proper transaction handling

### Phase 3: Migration System

1. Install and configure Flask-Migrate
2. Generate initial migration from current schema
3. Replace custom schema update logic

### Phase 4: Complete Refactoring

1. Remove custom JobStore implementation
2. Implement remaining repositories (User, Job)
3. Update all services to use repository pattern

## Dependencies

### Required Packages

- **SQLAlchemy**: ORM and database abstraction
- **Flask-Migrate**: Database migration management
- **Alembic**: Migration engine (dependency of Flask-Migrate)

### Internal Dependencies

- **Configuration Service**: For database URL and settings
- **Logging Service**: For error tracking and debugging

## Future Enhancements

### Advanced Features

- Read/write database splitting
- Database connection load balancing
- Automated backup and recovery
- Query performance monitoring

### Optimization

- Query result caching
- Database index optimization
- Connection pool tuning
- Async database operations

### Monitoring

- Database performance metrics
- Connection pool monitoring
- Query execution time tracking
- Error rate analysis
