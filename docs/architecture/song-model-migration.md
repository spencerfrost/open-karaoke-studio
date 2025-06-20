# Song Model & Metadata Cleanup: Complete Migration Plan

## Current Problem

We have a **legacy mess** where songs and metadata are treated as separate entities due to the historical `metadata.json` file approach. This creates:

1. **Dual model confusion**: `Song` vs `SongMetadata` Pydantic models
2. **Data conversion chaos**: Constant conversion between formats
3. **Missing SQLAlchemy models**: No proper database layer
4. **Legacy file dependencies**: `metadata.json` files still referenced
5. **Backward compatibility cruft**: Old code paths maintained unnecessarily

## Current Architecture Problems

### Problem 1: Fake Model Separation

```python
class Song(BaseModel):
    id: str
    title: str
    artist: str
    # ... 30+ fields

class SongMetadata(BaseModel):
    title: Optional[str] = None
    artist: Optional[str] = None
    # ... same fields but optional
```

**This is insane because:**

- They represent the SAME entity
- Metadata is just attributes of a song
- Forces constant conversion between types
- No clear data flow

### Problem 2: Missing Database Layer

We have Pydantic models but no proper SQLAlchemy models, leading to:

- Manual SQL or unclear ORM usage
- No migration strategy
- No relationship modeling
- No database constraints

### Problem 3: Legacy File System Dependencies

Code still references `metadata.json` files:

- Backward compatibility paths maintained
- File system as source of truth conflicts with database
- Sync operations between file system and database

## Complete Solution: Single Unified Model

### New Architecture: One Song Model

```python
# backend/app/db/models/song.py
from sqlalchemy import Column, String, Text, Float, Boolean, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from .base import Base
import uuid
from datetime import datetime, timezone

class Song(Base):
    """Single source of truth for all song data"""
    __tablename__ = "songs"

    # Primary identifiers
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Core song information
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False, default="Unknown Artist")
    duration = Column(Float)  # in seconds

    # Status and processing
    status = Column(String, nullable=False, default="processed")  # processed, processing, error
    processing_progress = Column(Float, default=0.0)  # 0.0 to 1.0

    # File paths (relative to library root)
    original_file_path = Column(String)  # original audio file
    vocal_file_path = Column(String)     # separated vocals
    instrumental_file_path = Column(String)  # separated instrumental

    # YouTube source data
    video_id = Column(String)
    source_url = Column(String)
    uploader = Column(String)
    uploader_id = Column(String)
    channel = Column(String)
    channel_id = Column(String)
    upload_date = Column(DateTime)

    # Rich metadata (iTunes, MusicBrainz, etc.)
    mbid = Column(String)  # MusicBrainz ID
    itunes_track_id = Column(Integer)
    itunes_artist_id = Column(Integer)
    release_title = Column(String)
    release_date = Column(String)
    genre = Column(String)
    language = Column(String)

    # Lyrics
    lyrics = Column(Text)
    synced_lyrics = Column(Text)  # LRC format

    # User data
    favorite = Column(Boolean, default=False)
    play_count = Column(Integer, default=0)
    last_played = Column(DateTime)

    # System metadata
    date_added = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    date_modified = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Raw metadata storage (for debugging/backup)
    youtube_raw_metadata = Column(Text)  # JSON string
    itunes_raw_metadata = Column(Text)   # JSON string

    def to_dict(self):
        """Convert to API response format"""
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "duration": self.duration,
            "status": self.status,
            "processingProgress": self.processing_progress,
            "videoId": self.video_id,
            "sourceUrl": self.source_url,
            "uploader": self.uploader,
            "channel": self.channel,
            "uploadDate": self.upload_date.isoformat() if self.upload_date else None,
            "genre": self.genre,
            "language": self.language,
            "lyrics": self.lyrics,
            "syncedLyrics": self.synced_lyrics,
            "favorite": self.favorite,
            "playCount": self.play_count,
            "lastPlayed": self.last_played.isoformat() if self.last_played else None,
            "dateAdded": self.date_added.isoformat() if self.date_added else None,
            # File paths for frontend
            "vocalPath": f"/api/songs/{self.id}/vocal" if self.vocal_file_path else None,
            "instrumentalPath": f"/api/songs/{self.id}/instrumental" if self.instrumental_file_path else None,
        }
```

### API Schema (Pydantic for validation only)

```python
# backend/app/schemas/song.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SongResponse(BaseModel):
    """API response schema - read-only"""
    id: str
    title: str
    artist: str
    duration: Optional[float]
    status: str
    processingProgress: float
    videoId: Optional[str]
    sourceUrl: Optional[str]
    # ... all fields for API response

class SongCreate(BaseModel):
    """Song creation schema - validation only"""
    title: str
    artist: str = "Unknown Artist"
    video_id: Optional[str] = None
    source_url: Optional[str] = None
    # ... only fields needed for creation

class SongUpdate(BaseModel):
    """Song update schema - validation only"""
    title: Optional[str] = None
    artist: Optional[str] = None
    favorite: Optional[bool] = None
    # ... only fields that can be updated
```

## Migration Plan: Complete Elimination of Legacy

### Phase 1: Database Migration

1. **Create new unified Song table**
2. **Migrate existing data** from current structure
3. **Drop old tables** (if any)
4. **Remove all metadata.json dependencies**

### Phase 2: Code Cleanup

1. **Remove SongMetadata Pydantic model entirely**
2. **Remove all file system metadata reading**
3. **Update all API endpoints** to use unified model
4. **Remove backward compatibility code**

### Phase 3: File System Cleanup

1. **Delete all metadata.json files**
2. **Restructure file organization** to be purely database-driven
3. **Update file serving logic** to use database paths

### Phase 4: Frontend Updates

1. **Update TypeScript interfaces** to match new API
2. **Remove metadata vs song confusion** in frontend
3. **Update all API calls** to use unified endpoints

## File Structure After Migration

```
karaoke_library/
├── {song-id}/
│   ├── original.mp3      # Original audio
│   ├── vocals.wav        # Separated vocals
│   ├── instrumental.wav  # Separated instrumental
│   └── cover.jpg         # Album art (optional)
└── database.db           # SQLite with all metadata
```

**NO MORE metadata.json files anywhere!**

## Critical Migration Steps

### 1. Data Migration Script

```python
def migrate_metadata_files_to_database():
    """One-time migration to eliminate metadata.json files"""
    for song_dir in karaoke_library.glob("*/"):
        metadata_file = song_dir / "metadata.json"
        if metadata_file.exists():
            # Read old metadata
            # Create new Song database record
            # Delete metadata.json
            # Update file paths in database
```

### 2. Remove All Legacy Code

- Search for "metadata.json" and delete ALL references
- Remove SongMetadata model completely
- Remove any file system metadata reading
- Remove conversion functions between Song/SongMetadata

### 3. Update All APIs

```python
# OLD (multiple models)
@song_bp.route("/<song_id>")
def get_song(song_id):
    song = get_song_operation(song_id)  # Returns DB model
    metadata = SongMetadata.from_song(song)  # Conversion hell
    return jsonify(Song.model_validate(song.to_dict()).model_dump())  # Clean conversion

# NEW (single source of truth)
@song_bp.route("/<song_id>")
def get_song(song_id):
    song = Song.query.filter_by(id=song_id).first()
    if not song:
        return jsonify({"error": "Song not found"}), 404
    return jsonify(song.to_dict())  # Direct, simple, clear
```

## Success Criteria

✅ **Zero metadata.json files exist**
✅ **Only one Song model in entire codebase**
✅ **No conversion between Song/SongMetadata**
✅ **Database is single source of truth**
✅ **No backward compatibility code**
✅ **Frontend uses unified API**

## Timeline

- **Day 1**: Create migration script and test on small dataset
- **Day 2**: Run full migration and update database models
- **Day 3**: Update all API endpoints
- **Day 4**: Update frontend to use new API
- **Day 5**: Delete all legacy code and files

This is a **one-way migration**. Once complete, we never look back at the metadata.json approach.
