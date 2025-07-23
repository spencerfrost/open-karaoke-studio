# iTunes Service Architecture

## Overview

The iTunes Service provides integration with Apple's iTunes Search API for metadata enhancement and cover art retrieval. It offers intelligent search capabilities, canonical release filtering, and high-quality artwork downloading to enrich song metadata.

## Current Implementation Status

**File**: `backend/app/services/itunes_service.py`  
**API**: iTunes Search API (Apple)  
**Status**: Fully implemented with comprehensive error handling

## Core Responsibilities

### 1. Metadata Search and Enhancement
- Search iTunes catalog for song metadata
- Filter and rank results for canonical releases
- Enhance existing metadata with iTunes data
- Provide fallback strategies for missing data

### 2. Cover Art Management
- Download high-resolution cover art from iTunes
- Handle multiple artwork resolution options
- Manage artwork URL optimization
- Provide fallback mechanisms for artwork retrieval

### 3. API Integration
- Handle iTunes Search API rate limiting
- Implement robust error handling and retries
- Manage different response formats
- Provide detailed logging for debugging

### 4. Data Quality Assurance
- Filter compilation and non-canonical releases
- Prioritize exact matches and streamable content
- Handle special characters and encoding issues
- Validate and clean metadata responses

## Service Interface

The iTunes Service provides several key functions for metadata operations:

```python
def search_itunes(artist: str, title: str, album: str = '', limit: int = 5) -> List[Dict[str, Any]]:
    """Search iTunes for song metadata with canonical release filtering"""

def get_itunes_cover_art(track_data: Dict[str, Any], song_dir: Path) -> Optional[str]:
    """Download cover art from iTunes artwork URLs"""

def enhance_metadata_with_itunes(metadata: Dict[str, Any], song_dir: Path) -> Dict[str, Any]:
    """Enhance song metadata with iTunes data and cover art"""
```

## Implementation Details

### Intelligent Search Strategy

The service implements sophisticated search logic to find the best matches:

```python
def search_itunes(artist, title, album='', limit=5):
    """
    Multi-strategy search with canonical filtering
    """
    # Build optimized search query
    search_terms = []
    if artist:
        search_terms.append(artist)
    if title:
        search_terms.append(title)
    if album:
        search_terms.append(album)
    
    search_query = " ".join(search_terms)
    
    # iTunes API parameters optimized for music search
    params = {
        'term': search_query,
        'entity': 'song',
        'media': 'music',
        'limit': min(50, limit * 5),  # Get more results for filtering
        'sort': 'recent',             # Newest releases first
        'country': 'US'
    }
    
    # Execute search with error handling
    response = requests.get(
        'https://itunes.apple.com/search',
        params=params,
        timeout=10,
        headers={'User-Agent': 'curl/8.0.0'}
    )
    
    # Process and filter results
    results = response.json().get('results', [])
    canonical_results = _filter_canonical_releases(results, artist, title)
    
    return canonical_results[:limit]
```

### Canonical Release Filtering

The service implements intelligent filtering to prioritize canonical releases over compilations:

```python
def _filter_canonical_releases(tracks, artist_query, title_query):
    """
    Score and rank tracks for canonical likelihood
    """
    scored_tracks = []
    
    for track in tracks:
        score = 0.0
        
        title = track.get('title', '').lower()
        artist = track.get('artist', '').lower()
        album = track.get('album', '').lower()
        
        # Exact matches get high scores
        if title == title_query.lower():
            score += 50
        elif title_query.lower() in title:
            score += 25
            
        if artist == artist_query.lower():
            score += 30
        elif artist_query.lower() in artist:
            score += 15
        
        # Avoid compilation indicators
        compilation_keywords = [
            'greatest hits', 'best of', 'compilation', 
            'collection', 'anthology', 'live', 'karaoke'
        ]
        
        if not any(keyword in album for keyword in compilation_keywords):
            score += 20
        
        # Prefer streamable content
        if track.get('isStreamable'):
            score += 10
            
        # Prefer non-explicit for karaoke
        if track.get('trackExplicitness') == 'notExplicit':
            score += 5
            
        scored_tracks.append({'track': track, 'score': score})
    
    # Sort by score, maintaining iTunes date order as secondary
    scored_tracks.sort(key=lambda x: x['score'], reverse=True)
    return [item['track'] for item in scored_tracks]
```

### High-Resolution Cover Art

The service automatically optimizes artwork URLs for high-resolution downloads:

```python
def get_itunes_cover_art(track_data, song_dir):
    """
    Download highest quality cover art available
    """
    artwork_url = (
        track_data.get('artworkUrl100') or 
        track_data.get('artworkUrl60') or 
        track_data.get('artworkUrl30')
    )
    
    if not artwork_url:
        return None
        
    # Optimize for high-resolution (600x600)
    high_res_url = artwork_url.replace(
        '100x100bb.jpg', '600x600bb.jpg'
    ).replace(
        '60x60bb.jpg', '600x600bb.jpg'
    ).replace(
        '30x30bb.jpg', '600x600bb.jpg'
    )
    
    cover_path = get_cover_art_path(song_dir)
    
    # Try high-resolution first, fallback to original
    if download_image(high_res_url, cover_path):
        return str(cover_path.relative_to(config.LIBRARY_DIR))
    elif download_image(artwork_url, cover_path):
        return str(cover_path.relative_to(config.LIBRARY_DIR))
    
    return None
```

### Comprehensive Metadata Enhancement

The service enhances metadata while preserving existing data:

```python
def enhance_metadata_with_itunes(metadata, song_dir):
    """
    Enhance metadata with iTunes data and cover art
    """
    artist = metadata.get('artist', '')
    title = metadata.get('title', '')
    
    if not artist or not title:
        return metadata
        
    # Search iTunes for best match
    itunes_results = search_itunes(artist, title, limit=1)
    if not itunes_results:
        return metadata
        
    itunes_data = itunes_results[0]
    
    # Download cover art
    cover_art_path = get_itunes_cover_art(itunes_data, song_dir)
    
    # Create enhanced metadata
    enhanced = metadata.copy()
    enhanced.update({
        # Core metadata (prefer iTunes if available)
        "title": itunes_data.get("title") or metadata.get("title"),
        "artist": itunes_data.get("artist") or metadata.get("artist"),
        "album": itunes_data.get("album") or metadata.get("album"),
        "genre": itunes_data.get("genre") or metadata.get("genre"),
        
        # iTunes-specific enhancements
        "releaseDate": itunes_data.get("releaseDateFormatted"),
        "releaseYear": itunes_data.get("releaseYear"),
        "duration": itunes_data.get("durationSeconds"),
        "trackNumber": itunes_data.get("trackNumber"),
        
        # iTunes identifiers for future reference
        "itunesTrackId": itunes_data.get("id"),
        "itunesArtistId": itunes_data.get("artistId"),
        "itunesCollectionId": itunes_data.get("albumId"),
        
        # Additional iTunes metadata
        "itunesExplicit": itunes_data.get("trackExplicitness") == "explicit",
        "itunesPreviewUrl": itunes_data.get("previewUrl"),
        "itunesRawMetadata": filter_itunes_metadata_for_storage(itunes_data),
    })
    
    if cover_art_path:
        enhanced["coverArt"] = cover_art_path
        
    return enhanced
```

## Error Handling and Resilience

### API Rate Limiting

The service implements comprehensive rate limiting and error handling:

```python
def handle_itunes_api_errors(response):
    """
    Handle various iTunes API error scenarios
    """
    if response.status_code == 403:
        logger.warning("iTunes API 403: Possible rate limiting or IP block")
        # Implement exponential backoff
        
    elif response.status_code == 429:
        retry_after = response.headers.get('Retry-After')
        logger.warning(f"iTunes API rate limited, retry after {retry_after}s")
        
    elif response.status_code >= 500:
        logger.error("iTunes API server error - may be temporary")
        
    # Log detailed error information for debugging
    logger.error(f"iTunes API Error Details:")
    logger.error(f"  Status: {response.status_code}")
    logger.error(f"  Headers: {dict(response.headers)}")
    logger.error(f"  Body: {response.text[:1000]}")
```

### Network Resilience

The service handles various network conditions:

```python
def robust_itunes_request(url, params, max_retries=3):
    """
    Make iTunes API request with retry logic
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(
                url, 
                params=params,
                timeout=10,
                headers={'User-Agent': 'curl/8.0.0'}
            )
            
            if response.status_code == 200:
                return response
                
            # Handle specific error codes
            if response.status_code == 429:  # Rate limited
                wait_time = 2 ** attempt  # Exponential backoff
                time.sleep(wait_time)
                continue
                
            # Other errors
            logger.warning(f"iTunes API attempt {attempt + 1} failed: {response.status_code}")
            
        except requests.RequestException as e:
            logger.warning(f"iTunes API network error attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise
                
    return None
```

## Integration Points

### Metadata Service Integration

The iTunes Service works closely with the Metadata Service:

```python
# In metadata_service.py
def enhance_with_external_sources(metadata, song_dir):
    """
    Enhance metadata using external sources including iTunes
    """
    enhanced = metadata.copy()
    
    # Try iTunes enhancement
    try:
        itunes_enhanced = enhance_metadata_with_itunes(enhanced, song_dir)
        if itunes_enhanced != enhanced:
            logger.info("Successfully enhanced metadata with iTunes")
            enhanced = itunes_enhanced
    except Exception as e:
        logger.warning(f"iTunes enhancement failed: {e}")
    
    return enhanced
```

### Song Service Integration

Song creation and updates utilize iTunes enhancement:

```python
# In song_service.py
def create_song_with_metadata(self, basic_metadata, song_dir):
    """
    Create song with enhanced metadata from iTunes
    """
    # Enhance with iTunes data
    enhanced_metadata = enhance_metadata_with_itunes(basic_metadata, song_dir)
    
    # Create song with enhanced data
    song = self.create_song(enhanced_metadata)
    
    return song
```

### YouTube Service Integration

YouTube downloads benefit from iTunes metadata enhancement:

```python
# In youtube workflow
def process_youtube_download(video_data):
    """
    Process YouTube download with iTunes enhancement
    """
    # Extract basic metadata from YouTube
    basic_metadata = extract_youtube_metadata(video_data)
    
    # Enhance with iTunes
    enhanced_metadata = enhance_metadata_with_itunes(
        basic_metadata, 
        song_directory
    )
    
    # Continue with enhanced metadata
    return create_song_from_metadata(enhanced_metadata)
```

## Performance Considerations

### Caching Strategy

```python
# iTunes response caching to reduce API calls
@lru_cache(maxsize=1000)
def cached_itunes_search(artist, title, album=''):
    """
    Cache iTunes search results to minimize API calls
    """
    return search_itunes(artist, title, album)
```

### Asynchronous Operations

```python
async def async_itunes_enhancement(metadata_list):
    """
    Process multiple iTunes enhancements concurrently
    """
    tasks = [
        enhance_metadata_with_itunes(metadata, song_dir)
        for metadata, song_dir in metadata_list
    ]
    
    return await asyncio.gather(*tasks, return_exceptions=True)
```

## Data Quality and Validation

### Metadata Validation

The service validates iTunes responses for quality:

```python
def validate_itunes_metadata(track_data):
    """
    Validate iTunes metadata quality
    """
    required_fields = ['title', 'artist']
    
    for field in required_fields:
        if not track_data.get(field):
            return False
            
    # Check for reasonable values
    if track_data.get('durationSeconds', 0) > 3600:  # > 1 hour
        logger.warning("Unusually long track duration from iTunes")
        
    return True
```

### Content Filtering

```python
def is_suitable_for_karaoke(track_data):
    """
    Determine if iTunes track is suitable for karaoke
    """
    # Avoid instrumental versions
    title = track_data.get('title', '').lower()
    if 'instrumental' in title or 'karaoke' in title:
        return False
        
    # Prefer non-explicit versions
    if track_data.get('trackExplicitness') == 'explicit':
        return False
        
    # Check if streamable
    if not track_data.get('isStreamable'):
        return False
        
    return True
```

## Testing and Debugging

### API Testing Utilities

The service includes comprehensive testing utilities:

```python
def test_itunes_api_access():
    """
    Test iTunes API access with detailed debugging
    """
    test_queries = [
        ("Coldplay", "Yellow"),
        ("The Beatles", "Hey Jude"),
        ("Queen", "Bohemian Rhapsody"),
    ]
    
    for artist, title in test_queries:
        results = search_itunes(artist, title, limit=3)
        print(f"\n{artist} - {title}:")
        
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result.get('title')} by {result.get('artist')}")
            print(f"     Album: {result.get('album')}")
            print(f"     Release: {result.get('releaseDateFormatted')}")
```

### Error Analysis

```python
def analyze_itunes_failures(error_log):
    """
    Analyze common iTunes API failure patterns
    """
    failure_patterns = {
        'rate_limit': 0,
        'network_timeout': 0,
        'no_results': 0,
        'invalid_response': 0
    }
    
    # Process error log and categorize failures
    # ... analysis logic ...
    
    return failure_patterns
```

## Dependencies

### Required Services
- **File Service**: For cover art download and path management
- **Metadata Service**: For metadata filtering and storage
- **Configuration Service**: For API settings and file paths

### External Dependencies
- **iTunes Search API**: Apple's public search interface
- **Requests library**: For HTTP communication
- **PIL/Pillow**: For image processing and validation

## Future Enhancements

### Advanced Features
- **Multiple Region Support**: Search iTunes stores in different countries
- **Preview Integration**: Use iTunes preview URLs for audio samples
- **Batch Processing**: Efficiently enhance multiple songs simultaneously
- **Alternative Sources**: Integrate additional metadata sources as fallbacks

### Performance Improvements
- **Connection Pooling**: Maintain persistent connections to iTunes API
- **Response Compression**: Enable gzip compression for API responses
- **Smart Caching**: Implement time-based cache invalidation
- **Parallel Processing**: Concurrent artwork downloads and API calls

### Data Enhancement
- **Lyrics Integration**: Extract lyrics from iTunes when available
- **Related Artists**: Use iTunes artist connections for recommendations
- **Genre Mapping**: Map iTunes genres to karaoke-friendly categories
- **Popularity Metrics**: Use iTunes ranking data for song prioritization