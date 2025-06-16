# Lyrics Service Architecture

## Overview

The Lyrics Service provides a centralized interface for all lyrics operations including fetching from external APIs, validating format, and managing lyrics storage. It abstracts lyrics handling across the application and enables consistent error handling and logging.

## Current Implementation Status

**File**: `backend/app/services/lyrics_service.py`  
**Interface**: Not yet implemented  
**Status**: Basic implementation exists, needs enhancement

## Core Responsibilities

### 1. External Lyrics Fetching
- Fetch lyrics from external APIs (e.g., LRCLIB)
- Handle API rate limiting and timeouts
- Cache results to minimize API calls
- Fall back between multiple lyrics sources

### 2. Lyrics Storage Management
- Read lyrics from filesystem or database
- Write lyrics to appropriate storage backend
- Manage lyrics file organization
- Handle file I/O errors gracefully

### 3. Lyrics Validation
- Validate lyrics format and completeness
- Check for minimum content requirements
- Detect and handle corrupt lyrics data
- Ensure lyrics meet quality standards

### 4. File Operations
- Check lyrics file existence
- Generate consistent file paths
- Create default lyrics content
- Handle lyrics file cleanup

## Service Interface

```python
class LyricsServiceInterface(Protocol):
    def fetch_lyrics(self, track_name: str, artist_name: str, album_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch lyrics from external sources or cache"""
        
    def get_lyrics(self, song_id: str) -> Optional[str]:
        """Get lyrics for a song from storage"""
        
    def save_lyrics(self, song_id: str, lyrics: str) -> bool:
        """Save lyrics for a song to storage"""
        
    def validate_lyrics(self, lyrics: str) -> bool:
        """Validate lyrics format and completeness"""
        
    def lyrics_file_exists(self, song_id: str) -> bool:
        """Check if lyrics file exists for a song"""
        
    def get_lyrics_file_path(self, song_id: str) -> str:
        """Get path to lyrics file for a song"""
        
    def create_default_lyrics(self, song_id: str) -> str:
        """Create default lyrics for a song"""
```

## Implementation Details

### External API Integration

The service integrates with external lyrics APIs while handling common failure scenarios:

```python
def fetch_lyrics(self, track_name, artist_name, album_name=None):
    """
    Fetch lyrics from external API with error handling
    """
    try:
        # Primary API attempt
        response = self._query_lrclib_api(track_name, artist_name, album_name)
        if response and self.validate_lyrics(response.get('lyrics', '')):
            return response
            
        # Fallback to alternative sources
        return self._try_fallback_sources(track_name, artist_name)
        
    except APIError as e:
        logger.warning(f"Lyrics API error for {track_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching lyrics: {e}")
        return None
```

### Storage Operations

Lyrics storage is abstracted to support both filesystem and database backends:

```python
def get_lyrics(self, song_id):
    """
    Retrieve lyrics from storage with fallback handling
    """
    try:
        # Try filesystem first
        lyrics_path = self.get_lyrics_file_path(song_id)
        if lyrics_path and os.path.exists(lyrics_path):
            with open(lyrics_path, 'r', encoding='utf-8') as f:
                lyrics = f.read()
                if self.validate_lyrics(lyrics):
                    return lyrics
                    
        # Fallback to database if configured
        return self._get_lyrics_from_database(song_id)
        
    except IOError as e:
        logger.error(f"Error reading lyrics file for {song_id}: {e}")
        return None
```

### Validation Logic

The service implements comprehensive lyrics validation:

```python
def validate_lyrics(self, lyrics):
    """
    Validate lyrics content and format
    """
    if not lyrics or not isinstance(lyrics, str):
        return False
        
    # Check minimum length
    if len(lyrics.strip()) < 10:
        return False
        
    # Check for common corruption indicators
    if self._contains_corruption_markers(lyrics):
        return False
        
    # Validate encoding
    try:
        lyrics.encode('utf-8')
    except UnicodeEncodeError:
        return False
        
    return True
```

## Integration Points

### Song Service Integration
The Lyrics Service is used by the Song Service for lyrics validation during song creation and updates:

```python
# In song_service.py
lyrics_valid = self.lyrics_service.validate_lyrics(song_data.get('lyrics', ''))
if not lyrics_valid:
    self.lyrics_service.create_default_lyrics(song_id)
```

### Sync Service Integration
During filesystem synchronization, the Sync Service relies on the Lyrics Service for reading existing lyrics:

```python
# In sync_service.py
existing_lyrics = self.lyrics_service.get_lyrics(song_id)
if not existing_lyrics:
    # Attempt to fetch from external sources
    fetched_lyrics = self.lyrics_service.fetch_lyrics(title, artist)
```

### API Endpoint Usage
API endpoints use the Lyrics Service for all lyrics operations:

```python
# In API routes
@app.route('/api/songs/<song_id>/lyrics', methods=['GET'])
def get_song_lyrics(song_id):
    lyrics = lyrics_service.get_lyrics(song_id)
    if not lyrics:
        return jsonify({'error': 'Lyrics not found'}), 404
    return jsonify({'lyrics': lyrics})
```

## Error Handling

The service implements comprehensive error handling for common failure scenarios:

- **API timeouts**: Graceful fallback to cache or alternative sources
- **File I/O errors**: Logging with fallback to database storage
- **Validation failures**: Default lyrics creation with user notification
- **Network issues**: Offline mode with cached lyrics only

## Performance Considerations

### Caching Strategy
- In-memory cache for frequently accessed lyrics
- Filesystem cache for external API responses
- Database cache for persistent storage

### Async Operations
- Background lyrics fetching for new songs
- Batch lyrics updates for library synchronization
- Non-blocking API calls with callbacks

## Dependencies

### Required Services
- **File Service**: For file path operations and directory management
- **Configuration Service**: For API keys and storage settings

### External Dependencies
- **LRCLIB API**: Primary lyrics source
- **HTTP client**: For API communication
- **File system**: For lyrics file storage

## Future Enhancements

### AI Integration
- AI-generated lyrics for songs without available lyrics
- Lyrics quality improvement using language models
- Automatic lyrics synchronization and timing

### Enhanced Sources
- Multiple lyrics API integration
- Community-contributed lyrics support
- Local lyrics database for offline operation

### Advanced Features
- Lyrics translation support
- Karaoke timing information extraction
- Lyrics analysis and categorization

## Testing Strategy

### Unit Tests
- Lyrics validation logic
- File operations with mocked filesystem
- API client with mocked responses

### Integration Tests
- End-to-end lyrics fetching workflow
- Storage backend switching
- Error handling scenarios

### Performance Tests
- API response time optimization
- Cache effectiveness measurement
- Concurrent lyrics operations