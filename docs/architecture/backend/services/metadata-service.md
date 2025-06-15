# Metadata Service Architecture

The Metadata Service provides centralized metadata processing and enrichment for Open Karaoke Studio. It integrates with multiple external APIs (iTunes, MusicBrainz, YouTube) to gather comprehensive song information, handles metadata normalization, and manages the storage and retrieval of rich song metadata.

## Overview

The Metadata Service acts as the central hub for all metadata operations, coordinating between multiple external data sources to provide comprehensive song information. It handles the complexity of different API formats, provides unified metadata models, and ensures consistent data quality across the application.

## Architecture

### Service Interface

The Metadata Service implements the `MetadataServiceInterface` protocol:

```python
# backend/app/services/interfaces/metadata_service.py
from typing import Protocol, List, Dict, Optional
from ...db.models import SongMetadata

class MetadataServiceInterface(Protocol):
    def search_metadata(self, artist: str = '', title: str = '', album: str = '') -> List[Dict]:
        """Search for song metadata across multiple sources"""
        
    def extract_metadata_from_youtube_info(self, info: Dict) -> SongMetadata:
        """Extract metadata from YouTube video information"""
        
    def enrich_with_itunes_metadata(self, metadata: SongMetadata) -> SongMetadata:
        """Enrich existing metadata with iTunes API data"""
        
    def search_itunes(self, artist: str, title: str, limit: int = 10) -> List[Dict]:
        """Search iTunes API for metadata"""
        
    def format_search_results(self, raw_results: List[Dict]) -> List[Dict]:
        """Format metadata results for frontend consumption"""
        
    def read_song_metadata(self, song_id: str) -> Optional[SongMetadata]:
        """Read metadata from file system"""
        
    def write_song_metadata(self, song_id: str, metadata: SongMetadata) -> None:
        """Write metadata to file system"""
```

### Service Implementation

The `MetadataService` coordinates multiple metadata sources:

```python
# backend/app/services/metadata_service.py
class MetadataService(MetadataServiceInterface):
    def __init__(
        self,
        file_service: FileServiceInterface = None,
        itunes_service: iTunesServiceInterface = None
    ):
        self.file_service = file_service or FileService()
        self.itunes_service = itunes_service or iTunesService()
        self.musicbrainz_service = MusicBrainzService()
```

## Data Sources Integration

### 1. iTunes API Integration

**Rich Metadata from Apple Music**:
```python
def search_itunes(self, artist: str, title: str, limit: int = 10) -> List[Dict]:
    """Search iTunes for comprehensive metadata"""
    search_params = {
        "term": f"{artist} {title}",
        "entity": "song",
        "limit": limit,
        "media": "music"
    }
    
    response = requests.get(self.ITUNES_API_URL, params=search_params)
    results = response.json().get("results", [])
    
    return [self._format_itunes_result(result) for result in results]

def _format_itunes_result(self, result: Dict) -> Dict:
    """Format iTunes API response to standardized format"""
    return {
        "source": "itunes",
        "musicbrainzId": result.get("trackId"),
        "title": result.get("trackName"),
        "artist": result.get("artistName"),
        "album": result.get("collectionName"),
        "year": self._extract_year(result.get("releaseDate")),
        "genre": result.get("primaryGenreName"),
        "duration": result.get("trackTimeMillis", 0) // 1000,
        "coverArt": result.get("artworkUrl100"),
        "previewUrl": result.get("previewUrl"),
        "explicit": result.get("trackExplicitness") == "explicit"
    }
```

**iTunes Metadata Features**:
- **Official Metadata**: Verified artist, title, album information
- **High-Quality Artwork**: Multiple resolution cover art (30x30, 60x60, 100x100)
- **Genre Classification**: Primary and secondary genre information  
- **Release Information**: Official release dates and label information
- **Preview Clips**: 30-second preview URLs for verification
- **Content Ratings**: Explicit content flagging

### 2. YouTube Metadata Extraction

**Video Information Processing**:
```python
def extract_metadata_from_youtube_info(self, info: Dict) -> SongMetadata:
    """Extract comprehensive metadata from YouTube video"""
    metadata = SongMetadata(
        # Basic video information
        title=info.get("title"),
        artist=info.get("uploader"),
        duration=info.get("duration"),
        
        # YouTube-specific metadata
        source="youtube",
        sourceUrl=info.get("webpage_url"),
        videoId=info.get("id"),
        videoTitle=info.get("title"),
        uploader=info.get("uploader"),
        uploaderId=info.get("uploader_id"),
        channel=info.get("channel"),
        channelId=info.get("channel_id"),
        description=info.get("description"),
        uploadDate=self._parse_upload_date(info.get("upload_date")),
        
        # Visual assets
        thumbnail=self._get_best_thumbnail_url(info),
        youtubeThumbnailUrls=self._extract_thumbnail_urls(info),
        
        # Technical information
        youtubeDuration=info.get("duration")
    )
    
    return metadata
```

**YouTube Metadata Features**:
- **Video Context**: Title, description, upload date, view count
- **Channel Information**: Channel name, channel ID, subscriber count
- **Technical Data**: Duration, format information, quality metrics
- **Thumbnail Assets**: Multiple resolution thumbnails
- **Social Metrics**: View count, like/dislike ratios (when available)

### 3. MusicBrainz Integration

**Comprehensive Music Database**:
```python
def search_musicbrainz(self, artist: str = '', title: str = '', album: str = '') -> List[Dict]:
    """Search MusicBrainz for authoritative music metadata"""
    query_parts = []
    if artist:
        query_parts.append(f'artist:"{artist}"')
    if title:
        query_parts.append(f'recording:"{title}"')
    if album:
        query_parts.append(f'release:"{album}"')
    
    query = " AND ".join(query_parts)
    
    try:
        result = musicbrainzngs.search_recordings(
            query=query,
            limit=10,
            inc=["artist-credits", "releases", "genres"]
        )
        
        return [self._format_musicbrainz_result(recording) 
                for recording in result.get("recording-list", [])]
                
    except Exception as e:
        logger.error(f"MusicBrainz search failed: {e}")
        return []
```

**MusicBrainz Features**:
- **Authoritative IDs**: Unique MusicBrainz Recording and Release IDs
- **Relationship Data**: Artist relationships, collaborations, remixes
- **Release Information**: Multiple release versions, formats, dates
- **Genre Classification**: Community-curated genre and style tags
- **Language Information**: Lyric language and regional variants

## Metadata Enrichment Workflow

### Multi-Source Strategy

The service uses a cascading approach to gather the most comprehensive metadata:

```python
def enrich_song_metadata(self, base_metadata: SongMetadata) -> SongMetadata:
    """Enrich metadata using multiple sources"""
    enriched = base_metadata.copy()
    
    # 1. Start with YouTube metadata (if source is YouTube)
    if enriched.source == "youtube":
        # Already have YouTube data
        pass
    
    # 2. Enhance with iTunes official metadata
    if enriched.artist and enriched.title:
        itunes_results = self.search_itunes(enriched.artist, enriched.title, limit=3)
        if itunes_results:
            best_match = self._find_best_itunes_match(enriched, itunes_results)
            if best_match:
                enriched = self._merge_itunes_metadata(enriched, best_match)
    
    # 3. Add MusicBrainz authoritative IDs
    if enriched.artist and enriched.title:
        mb_results = self.search_musicbrainz(enriched.artist, enriched.title)
        if mb_results:
            best_mb_match = self._find_best_musicbrainz_match(enriched, mb_results)
            if best_mb_match:
                enriched.mbid = best_mb_match.get("mbid")
                enriched.releaseId = best_mb_match.get("release_id")
    
    return enriched
```

### Smart Matching Algorithm

**Fuzzy Matching for Cross-Source Correlation**:
```python
def _find_best_itunes_match(self, target: SongMetadata, candidates: List[Dict]) -> Optional[Dict]:
    """Find best iTunes match using fuzzy string matching"""
    if not candidates:
        return None
    
    best_match = None
    best_score = 0.0
    
    for candidate in candidates:
        # Calculate similarity scores
        title_score = fuzz.ratio(
            target.title.lower() if target.title else "",
            candidate.get("title", "").lower()
        )
        artist_score = fuzz.ratio(
            target.artist.lower() if target.artist else "",
            candidate.get("artist", "").lower()
        )
        
        # Weighted average (title is more important)
        combined_score = (title_score * 0.7) + (artist_score * 0.3)
        
        if combined_score > best_score and combined_score > 70:  # Threshold
            best_score = combined_score
            best_match = candidate
    
    return best_match
```

## Metadata Storage and Persistence

### File System Storage

**JSON Metadata Files**:
```python
def write_song_metadata(self, song_id: str, metadata: SongMetadata) -> None:
    """Write metadata to organized file structure"""
    try:
        song_dir = self.file_service.get_song_directory(song_id)
        metadata_path = song_dir / "metadata.json"
        
        # Convert to serializable format
        metadata_dict = metadata.model_dump(mode='json')
        
        # Write with proper formatting
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata_dict, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Metadata written for song {song_id}")
        
    except Exception as e:
        logger.error(f"Failed to write metadata for {song_id}: {e}")
        raise ServiceError(f"Failed to write metadata: {e}")

def read_song_metadata(self, song_id: str) -> Optional[SongMetadata]:
    """Read metadata from file system"""
    try:
        song_dir = self.file_service.get_song_directory(song_id)
        metadata_path = song_dir / "metadata.json"
        
        if not metadata_path.exists():
            return None
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata_dict = json.load(f)
        
        return SongMetadata(**metadata_dict)
        
    except Exception as e:
        logger.warning(f"Failed to read metadata for {song_id}: {e}")
        return None
```

### Database Integration

**Metadata Synchronization**:
```python
def sync_metadata_to_database(self, song_id: str, metadata: SongMetadata) -> None:
    """Sync metadata to database for search and queries"""
    try:
        # Update database record with key metadata fields
        database.update_song_metadata(
            song_id=song_id,
            title=metadata.title,
            artist=metadata.artist,
            album=metadata.releaseTitle,
            duration=metadata.duration,
            genre=metadata.genre,
            year=self._extract_year(metadata.releaseDate),
            source=metadata.source
        )
        
        logger.debug(f"Database metadata synced for song {song_id}")
        
    except Exception as e:
        logger.error(f"Failed to sync metadata to database: {e}")
        # Continue - file system is primary storage
```

## API Integration Patterns

### Frontend Metadata Search

**Unified Search Interface**:
```python
def search_metadata(self, artist: str = '', title: str = '', album: str = '') -> List[Dict]:
    """Unified metadata search across all sources"""
    all_results = []
    
    # Search iTunes (primary source for quality)
    if artist or title:
        itunes_results = self.search_itunes(artist, title)
        all_results.extend(itunes_results)
    
    # Search MusicBrainz (secondary for completeness)  
    if artist or title or album:
        mb_results = self.search_musicbrainz(artist, title, album)
        all_results.extend(mb_results)
    
    # Format and deduplicate results
    formatted_results = self.format_search_results(all_results)
    return self._deduplicate_results(formatted_results)

def format_search_results(self, raw_results: List[Dict]) -> List[Dict]:
    """Format results for consistent frontend consumption"""
    formatted = []
    
    for result in raw_results:
        formatted.append({
            "musicbrainzId": result.get("musicbrainzId"),
            "title": result.get("title"),
            "artist": result.get("artist"),
            "album": result.get("album"),
            "year": result.get("year"),
            "genre": result.get("genre"),
            "duration": result.get("duration"),
            "coverArt": result.get("coverArt"),
            "source": result.get("source"),
            "previewUrl": result.get("previewUrl"),
            "explicit": result.get("explicit", False)
        })
    
    return formatted
```

### Thin Controller Pattern

```python
# backend/app/api/metadata.py
@metadata_bp.route('/search', methods=['GET'])
def search_metadata():
    """Metadata search endpoint using service layer"""
    try:
        artist = request.args.get('artist', '')
        title = request.args.get('title', '')
        album = request.args.get('album', '')
        
        metadata_service = MetadataService()
        results = metadata_service.search_metadata(artist, title, album)
        
        return jsonify(results)
        
    except ServiceError as e:
        return jsonify({"error": str(e)}), 500
```

## Error Handling and Resilience

### API Failure Management

**Graceful Degradation**:
```python
def search_metadata(self, artist: str = '', title: str = '') -> List[Dict]:
    """Search with graceful degradation"""
    results = []
    
    # Try primary source (iTunes)
    try:
        itunes_results = self.search_itunes(artist, title)
        results.extend(itunes_results)
        logger.info(f"iTunes search successful: {len(itunes_results)} results")
    except Exception as e:
        logger.warning(f"iTunes search failed: {e}")
        # Continue with other sources
    
    # Try secondary source (MusicBrainz)
    try:
        mb_results = self.search_musicbrainz(artist, title)
        results.extend(mb_results)
        logger.info(f"MusicBrainz search successful: {len(mb_results)} results")
    except Exception as e:
        logger.warning(f"MusicBrainz search failed: {e}")
        # Continue - may have results from iTunes
    
    if not results:
        logger.warning("All metadata sources failed")
        # Return basic metadata structure
        return self._create_fallback_metadata(artist, title)
    
    return self.format_search_results(results)
```

### Rate Limiting and Caching

**Respectful API Usage**:
```python
class MetadataService:
    def __init__(self):
        self.cache = TTLCache(maxsize=1000, ttl=3600)  # 1 hour cache
        self.rate_limiter = RateLimiter(calls=100, period=60)  # 100/minute
    
    def search_itunes(self, artist: str, title: str) -> List[Dict]:
        # Check cache first
        cache_key = f"itunes:{artist}:{title}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Rate limiting
        with self.rate_limiter:
            results = self._do_itunes_search(artist, title)
            self.cache[cache_key] = results
            return results
```

## Related Services

- **[iTunes Service](./itunes-service.md)** - Specialized iTunes API integration
- **[File Service](./file-service.md)** - Metadata file storage and retrieval
- **[YouTube Service](./youtube-service.md)** - Video metadata extraction
- **[Song Service](./song-service.md)** - Song metadata coordination

---

**Implementation Status**: ✅ Implemented  
**Location**: `backend/app/services/metadata_service.py`  
**Interface**: `backend/app/services/interfaces/metadata_service.py`  
**API Integration**: `backend/app/api/metadata.py`
