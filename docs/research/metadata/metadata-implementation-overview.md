# Metadata System Implementation Overview

**Last Updated**: June 15, 2025
**Status**: ✅ Implemented
**Architecture**: Multi-source metadata aggregation with iTunes + YouTube integration

## 🎯 Current Implementation Status

### ✅ Completed Features

- **Backend Architecture**: Complete metadata pipeline with iTunes and YouTube integration
- **Database Schema**: Rich metadata storage with Phase 1A/1B fields implemented
- **API Endpoints**: Full CRUD operations for song metadata with enhanced fields
- **Data Processing**: Automatic metadata enhancement during YouTube download pipeline
- **Cover Art System**: High-resolution cover art download and storage (600x600)
- **Type Safety**: Synchronized Song models between backend and frontend

### 🔄 Active Development Areas

- **Frontend Integration**: Genre display and album art integration (Issue 011h)
- **Metadata Editing**: iTunes metadata search and update UI components
- **Data Quality**: Ongoing improvements to metadata matching algorithms

## 🏗️ System Architecture

### Data Sources

```
Primary Metadata Sources:
├── iTunes API (Apple Music Catalog)
│   ├── Official song metadata (artist, title, album, genre)
│   ├── High-resolution album artwork (30x30 → 600x600)
│   ├── Preview URLs and track identifiers
│   └── Release dates and content ratings
├── YouTube API (Video Context)
│   ├── Video metadata (title, description, duration)
│   ├── Channel information and upload details
│   ├── Thumbnail URLs and video tags
│   └── Video-specific duration (separate from track duration)
└── User Input (Manual Overrides)
    ├── Custom metadata corrections
    ├── Favorite status and user ratings
    └── Custom artwork uploads
```

### Backend Data Flow

```
YouTube Download Pipeline:
1. Extract basic metadata from yt-dlp
2. Enhance with iTunes API search (get_enhanced_song_info)
3. Download high-resolution cover art (600x600)
4. Store comprehensive metadata in database
5. Serve via REST API with camelCase conversion

Database Schema (DbSong):
├── Core Fields: id, title, artist, album, duration, genre
├── iTunes Fields: itunes_track_id, itunes_artwork_urls, itunes_preview_url
├── YouTube Fields: video_id, youtube_duration, youtube_thumbnail_urls
├── File Paths: vocals_path, instrumental_path, cover_art_path
└── User Data: favorite, date_added, play_count
```

### Frontend Integration

```
TypeScript Song Interface:
├── Core metadata display in song cards and details
├── iTunes integration for metadata editing
├── Album art prioritization (cover art > thumbnails)
├── Genre display and filtering capabilities
└── Metadata quality indicators and source badges
```

## 🔧 Technical Implementation

### Key Backend Services

#### 1. iTunes Integration Service

**Location**: `backend/app/services/itunes_service.py`

**Features**:

- Search iTunes catalog for song matches
- Extract high-quality metadata and artwork
- Handle rate limiting and error responses
- Support for multiple search strategies (artist+title, album search)

**Implementation**:

```python
def get_enhanced_song_info(title: str, artist: str) -> Optional[Dict]:
    """
    Searches iTunes API and returns enhanced metadata
    Returns None if no suitable match found
    """
    # Multi-strategy search with confidence scoring
    # Returns standardized metadata format
```

#### 2. YouTube Service Integration

**Location**: `backend/app/services/youtube_service.py`

**Features**:

- Extract metadata from yt-dlp info
- Automatic iTunes enhancement during download
- Dual duration tracking (video vs. track duration)
- Complete YouTube context preservation

**Integration Point**:

```python
def download_video(url: str) -> ProcessingResult:
    # 1. Extract YouTube metadata
    # 2. Call iTunes enhancement
    # 3. Download cover art
    # 4. Save to database with full metadata
```

#### 3. Metadata Management

**Location**: `backend/app/db/models/song.py`

**Current Schema**:

```python
class DbSong(Base):
    # Core metadata
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    album = Column(String, nullable=True)
    genre = Column(String, nullable=True)
    duration = Column(Float, nullable=True)

    # iTunes integration
    itunes_track_id = Column(Integer, nullable=True)
    itunes_artwork_urls = Column(Text, nullable=True)  # JSON array
    itunes_preview_url = Column(String, nullable=True)

    # YouTube context
    video_id = Column(String, nullable=True)
    youtube_duration = Column(Float, nullable=True)
    youtube_thumbnail_urls = Column(Text, nullable=True)  # JSON array

    # File management
    cover_art_path = Column(String, nullable=True)
    vocals_path = Column(String, nullable=True)
    instrumental_path = Column(String, nullable=True)
```

### Frontend Architecture

#### 1. Song Type Definition

**Location**: `frontend/src/types/Song.ts`

**Current Interface**:

```typescript
export interface Song {
  // Core fields (matches backend exactly)
  id: string;
  title: string;
  artist: string;
  album: string;
  duration: number;
  genre?: string;

  // iTunes metadata
  itunesTrackId?: number;
  itunesPreviewUrl?: string;
  itunesArtworkUrls?: {
    60?: string;
    100?: string;
    600?: string;
  };

  // YouTube metadata
  videoId?: string;
  youtubeDuration?: number;
  youtubeThumbnailUrls?: {
    default?: string;
    medium?: string;
    high?: string;
  };

  // File paths
  coverArt?: string;
  vocalPath?: string;
  instrumentalPath?: string;
}
```

#### 2. Metadata Display Components

**Locations**: `frontend/src/components/songs/`

**Current Implementation**:

- **SongCard**: Basic metadata display with cover art prioritization
- **SongDetailsDialog**: Complete metadata view with quality indicators
- **MetadataEditor**: iTunes search and metadata update interface
- **PrimarySongDetails**: Organized metadata grid with source badges

#### 3. API Integration

**Location**: `frontend/src/services/api.ts`

**Features**:

- Automatic camelCase conversion from backend snake_case
- Type-safe requests with full Song interface support
- Error handling for missing metadata fields
- Support for PATCH operations to update metadata

## 📊 Data Quality & Enhancement

### Metadata Enhancement Pipeline

#### 1. iTunes Matching Strategy

```
Search Process:
1. Primary: "{artist} {title}" search
2. Fallback: "{title}" search with artist filtering
3. Confidence scoring based on:
   - Artist name similarity (Levenshtein distance)
   - Title similarity
   - Duration matching (±10% tolerance)
4. Manual override capability via frontend
```

#### 2. Cover Art Management

```
Resolution Priority:
1. iTunes 600x600 (preferred)
2. iTunes 100x100 (fallback)
3. YouTube maxres thumbnail
4. YouTube high thumbnail
5. Default placeholder

Storage:
- High-resolution files stored in song directories
- Multiple format support (JPG, PNG, WebP)
- Automatic format conversion and optimization
```

#### 3. Data Validation

```
Quality Checks:
- Required fields: title, artist (minimum viable)
- Optional enhancement: album, genre, cover art
- Duration validation against actual audio file
- iTunes ID validation for authentic metadata
- Duplicate detection and merging
```

## 🎨 User Experience Features

### Current Frontend Capabilities

#### 1. Song Library

- **Genre Display**: Shows iTunes-derived genre information
- **Album Art**: Prioritizes high-resolution cover art over thumbnails
- **Source Indicators**: Visual badges showing metadata sources (iTunes + YouTube)
- **Quality Indicators**: Shows metadata completeness percentage

#### 2. Song Details

- **Comprehensive View**: All available metadata in organized display
- **iTunes Preview**: 30-second audio previews via iTunes API
- **Metadata Quality**: Visual indicators for data completeness
- **Source Attribution**: Clear indication of data sources

#### 3. Metadata Editing

- **iTunes Search**: Direct search of Apple Music catalog
- **Comparison View**: Side-by-side current vs. new metadata
- **Selective Updates**: Choose which fields to update
- **Conflict Resolution**: Handle mismatched data gracefully

### Future Enhancement Areas

#### 1. Smart Features (Planned)

- **Auto-Categorization**: Genre-based smart playlists
- **Duplicate Detection**: Identify and merge duplicate songs
- **Metadata Suggestions**: AI-powered metadata recommendations
- **Batch Operations**: Bulk metadata updates and corrections

#### 2. Advanced Integration (Future)

- **MusicBrainz Integration**: Additional metadata source
- **Last.fm Integration**: Scrobbling and social features
- **Spotify Integration**: Playlist synchronization
- **User Contributions**: Community-driven metadata improvements

## 🔧 Developer Reference

### Adding New Metadata Fields

#### 1. Backend Changes

```python
# 1. Add database column
class DbSong(Base):
    new_field = Column(String, nullable=True)

# 2. Update Song model
class Song(BaseModel):
    new_field: Optional[str] = None

# 3. Update DbSong.to_dict() method
def to_dict(self):
    return {
        # ...existing fields...
        "newField": self.new_field,  # Convert snake_case to camelCase
    }
```

#### 2. Frontend Changes

```typescript
// 1. Update Song interface
export interface Song {
  // ...existing fields...
  newField?: string;
}

// 2. Add to display components
<div>
  <span className="font-medium text-muted-foreground">New Field</span>
  <p className="text-foreground">{song.newField || "Unknown"}</p>
</div>;
```

### Testing Metadata Integration

#### 1. Backend Testing

```python
# Test iTunes enhancement
def test_itunes_enhancement():
    result = get_enhanced_song_info("Bohemian Rhapsody", "Queen")
    assert result["genre"] is not None
    assert result["album"] == "A Night at the Opera"

# Test database storage
def test_metadata_storage():
    song = DbSong.from_metadata(song_id, enhanced_metadata)
    assert song.itunes_track_id is not None
```

#### 2. Frontend Testing

```typescript
// Test metadata display
test("displays genre when available", () => {
  const song = mockSong({ genre: "Rock" });
  render(<SongCard song={song} />);
  expect(screen.getByText("Rock")).toBeInTheDocument();
});

// Test missing metadata graceful handling
test("handles missing metadata gracefully", () => {
  const song = mockSong({ genre: undefined });
  render(<SongCard song={song} />);
  expect(screen.getByText("Unknown")).toBeInTheDocument();
});
```

## 📈 Performance Considerations

### Database Optimization

- **Indexing**: Genre, artist, album fields indexed for fast filtering
- **JSON Storage**: iTunes and YouTube raw metadata stored as JSON for flexibility
- **Query Optimization**: Efficient joins for metadata-heavy queries
- **Caching**: API response caching to reduce external service calls

### Frontend Performance

- **Lazy Loading**: Metadata loaded on-demand for large libraries
- **Image Optimization**: Cover art served in multiple resolutions
- **Virtual Scrolling**: Efficient rendering for large song lists
- **Memoization**: Expensive metadata calculations cached

### API Rate Limiting

- **iTunes API**: Respectful rate limiting with exponential backoff
- **Batch Processing**: Group operations to minimize API calls
- **Caching Strategy**: Local caching of successful API responses
- **Error Handling**: Graceful degradation when APIs are unavailable

## 🚀 Current Implementation Status

### ✅ Production-Ready Features

1. **Complete Backend Pipeline**: iTunes + YouTube metadata integration
2. **Database Schema**: Rich metadata storage with all planned fields
3. **API Layer**: Full CRUD operations with type safety
4. **Cover Art System**: High-resolution artwork download and management
5. **Error Handling**: Graceful degradation and retry logic

### 🔄 Active Development

1. **Frontend Genre Display**: Adding genre information to song cards
2. **Album Art Integration**: Replacing thumbnails with cover art
3. **Metadata Editor**: iTunes search and update interface
4. **Type Synchronization**: Ensuring frontend/backend type alignment

### 📋 Future Roadmap

1. **Advanced Search**: Metadata-powered search and filtering
2. **Smart Playlists**: Genre and metadata-based auto-playlists
3. **Batch Operations**: Bulk metadata updates and corrections
4. **Additional Sources**: MusicBrainz, Last.fm integration

---

## 🔗 Related Documentation

- **[Backend Architecture](../../../architecture/backend/services/metadata-service.md)** - Detailed service implementation
- **[Frontend Components](../../../architecture/frontend/components/song-details-system.md)** - UI implementation patterns
- **[API Documentation](../../../api/metadata.md)** - REST API reference
- **[Database Schema](../../../architecture/backend/database-design.md)** - Data model details

---

**Implementation Status**: ✅ Core system implemented and operational
**Next Steps**: Complete frontend integration and metadata editing features
**Maintenance**: Regular updates to iTunes matching algorithms and data quality improvements

This metadata system provides the foundation for rich song information throughout Open Karaoke Studio, enabling better search, organization, and user experience while maintaining high data quality and performance.
