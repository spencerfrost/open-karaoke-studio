# Songs & Artists API Endpoints

This document covers the dual display library API endpoints that power the new fuzzy search and artist browsing interface.

## Overview

The Songs & Artists API provides endpoints for the dual display library system that separates song search results from artist browsing. This architecture allows users to:

- **Search for specific songs** with fuzzy matching and infinite pagination
- **Browse artists alphabetically** with song counts and expandable sections
- **Seamlessly switch** between search and browsing modes

## Base URL
```
/api/songs
```

## Endpoints

### 1. Search Songs with Fuzzy Matching

**Endpoint:** `GET /api/songs/search`

Search for songs across the entire library with fuzzy matching capabilities.

#### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query (fuzzy matching enabled) |
| `offset` | integer | No | Number of results to skip (default: 0) |
| `limit` | integer | No | Results per page (default: 20, max: 100) |
| `group_by_artist` | boolean | No | Group results by artist (default: false) |
| `sort` | string | No | Sort order: `relevance`, `title`, `artist`, `dateAdded` (default: `relevance`) |
| `direction` | string | No | Sort direction: `asc`, `desc` (default: `desc`) |

#### Response
```json
{
  "songs": [
    {
      "id": "uuid-string",
      "title": "Song Title",
      "artist": "Artist Name",
      "album": "Album Name",
      "year": 2023,
      "duration": 240,
      "coverArt": "/api/songs/uuid/cover",
      "audioPreview": "/api/songs/uuid/preview",
      "instrumentalTrack": "/api/songs/uuid/instrumental",
      "vocalTrack": "/api/songs/uuid/vocals",
      "createdAt": "2023-01-01T00:00:00Z",
      "processingStatus": "completed"
    }
  ],
  "pagination": {
    "total": 150,
    "limit": 20,
    "offset": 0,
    "hasMore": true
  }
}
```

#### Example Request
```bash
curl "http://localhost:5000/api/songs/search?q=bohemian&offset=0&limit=20"
```

### 2. Browse Artists Alphabetically

**Endpoint:** `GET /api/songs/artists`

Browse artists with song counts, organized alphabetically for efficient browsing.

#### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `search` | string | No | Optional search term to filter artists |
| `offset` | integer | No | Number of artists to skip (default: 0) |
| `limit` | integer | No | Artists per page (default: 100, max: 200) |

#### Response
```json
{
  "artists": [
    {
      "name": "Artist Name",
      "songCount": 15,
      "firstLetter": "A",
      "coverArt": "/api/artists/artist-name/cover",
      "genres": ["Rock", "Pop"],
      "latestSong": "2023-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "total": 250,
    "limit": 50,
    "offset": 0,
    "hasMore": true
  }
}
```

#### Example Request
```bash
curl "http://localhost:5000/api/songs/artists?offset=0&limit=50&search=rock"
```

### 3. Get Songs by Artist

**Endpoint:** `GET /api/songs/by-artist/{artist_name}`

Retrieve all songs for a specific artist with pagination.

#### Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `artist_name` | string | Yes | URL-encoded artist name |
| `offset` | integer | No | Number of songs to skip (default: 0) |
| `limit` | integer | No | Songs per page (default: 20, max: 100) |
| `sort` | string | No | Sort order: `title`, `album`, `year`, `dateAdded` (default: `title`) |
| `direction` | string | No | Sort direction: `asc`, `desc` (default: `asc`) |

#### Response
```json
{
  "artist": {
    "name": "Artist Name",
    "songCount": 15,
    "albums": ["Album 1", "Album 2"],
    "genres": ["Rock", "Pop"],
    "coverArt": "/api/artists/artist-name/cover"
  },
  "songs": [
    {
      "id": "uuid-string",
      "title": "Song Title",
      "album": "Album Name",
      "year": 2023,
      "duration": 240,
      "trackNumber": 1,
      "coverArt": "/api/songs/uuid/cover",
      "audioPreview": "/api/songs/uuid/preview",
      "instrumentalTrack": "/api/songs/uuid/instrumental",
      "vocalTrack": "/api/songs/uuid/vocals",
      "createdAt": "2023-01-01T00:00:00Z",
      "processingStatus": "completed"
    }
  ],
  "pagination": {
    "total": 15,
    "limit": 50,
    "offset": 0,
    "hasMore": false
  }
}
```

#### Example Request
```bash
curl "http://localhost:5000/api/songs/by-artist/Queen?offset=0&limit=50&sort=year&direction=asc"
```

## Search Features

### Fuzzy Matching
The search endpoint uses fuzzy string matching to find songs even with:
- **Typos**: "bohemain" finds "Bohemian Rhapsody"
- **Partial matches**: "queen boh" finds "Queen - Bohemian Rhapsody"
- **Word order**: "rhapsody bohemian" finds "Bohemian Rhapsody"
- **Missing words**: "boh rhap" finds "Bohemian Rhapsody"

### Search Scope
Searches across:
- Song titles
- Artist names
- Album names
- Combined metadata (e.g., "Artist - Title")

### Performance Optimizations
- **Debounced requests**: Frontend implements 300ms debouncing
- **Result caching**: Search results cached for common queries
- **Pagination**: Large result sets split across pages
- **Index optimization**: Database indexes for fast text searching

## Artist Browsing Features

### Alphabetical Organization
- Artists sorted alphabetically by name
- Special handling for "The" prefixes (configurable)
- Numeric artists grouped under "#"
- Case-insensitive sorting

### Performance Features
- **Lazy loading**: Artist songs loaded only when expanded
- **Conditional queries**: API calls prevented for collapsed artists
- **Infinite scroll**: Artists loaded progressively
- **Song count caching**: Artist metadata cached for performance

## Error Handling

### Common Error Responses

#### 400 Bad Request
```json
{
  "error": "Invalid search query",
  "message": "Search query must be at least 1 character",
  "code": "INVALID_QUERY"
}
```

#### 404 Not Found
```json
{
  "error": "Artist not found",
  "message": "No artist found with name 'NonExistentArtist'",
  "code": "ARTIST_NOT_FOUND"
}
```

#### 500 Internal Server Error
```json
{
  "error": "Search service unavailable",
  "message": "Search index temporarily unavailable",
  "code": "SEARCH_SERVICE_ERROR"
}
```

## Integration Examples

### Frontend Integration
```typescript
// Search songs with fuzzy matching
const searchSongs = async (query: string, offset: number = 0) => {
  const response = await fetch(
    `/api/songs/search?q=${encodeURIComponent(query)}&offset=${offset}`
  );
  return response.json();
};

// Browse artists alphabetically
const browseArtists = async (offset: number = 0, search?: string) => {
  const params = new URLSearchParams({ offset: offset.toString() });
  if (search) params.append('search', search);
  
  const response = await fetch(`/api/songs/artists?${params}`);
  return response.json();
};

// Get songs for specific artist
const getArtistSongs = async (artistName: string, offset: number = 0) => {
  const response = await fetch(
    `/api/songs/by-artist/${encodeURIComponent(artistName)}?offset=${offset}`
  );
  return response.json();
};
```

### React Query Integration
```typescript
// Infinite query for song search
const useInfiniteSongSearch = (query: string) => {
  return useInfiniteQuery({
    queryKey: ['songs', 'search', query],
    queryFn: ({ pageParam = 0 }) => searchSongs(query, pageParam),
    getNextPageParam: (lastPage) => 
      lastPage.pagination.hasMore ? lastPage.pagination.offset + lastPage.pagination.limit : undefined,
    enabled: query.length > 0
  });
};

// Infinite query for artist browsing
const useInfiniteArtists = (search?: string) => {
  return useInfiniteQuery({
    queryKey: ['artists', 'browse', search],
    queryFn: ({ pageParam = 0 }) => browseArtists(pageParam, search),
    getNextPageParam: (lastPage) => 
      lastPage.pagination.hasMore ? lastPage.pagination.offset + lastPage.pagination.limit : undefined
  });
};

// Conditional query for artist songs (only when expanded)
const useArtistSongs = (artistName: string, isExpanded: boolean) => {
  return useQuery({
    queryKey: ['artists', artistName, 'songs'],
    queryFn: () => getArtistSongs(artistName),
    enabled: isExpanded && artistName.length > 0
  });
};
```

## Implementation Notes

### Backend Implementation
- **Database**: Uses SQLite with full-text search indexes
- **Fuzzy matching**: Implemented with trigram similarity
- **Caching**: Artist metadata cached for performance
- **Pagination**: Cursor-based pagination for large datasets

### Frontend Integration
- **Dual display**: Separate sections for songs and artists
- **State management**: React Query for API state
- **Performance**: Conditional loading and infinite scroll
- **UX**: Debounced search and loading states

### Performance Considerations
- **Search debouncing**: 300ms delay to reduce API calls
- **Conditional loading**: Artist songs only loaded when needed
- **Result caching**: Common searches cached client-side
- **Pagination**: Large datasets split for better performance

## Related Documentation
- **[Library Management User Guide](../user-guide/library-management.md)** - User-facing documentation
- **[Frontend Library Components](../architecture/frontend/components.md)** - Component architecture
- **[Backend Song Operations](../architecture/backend/song-operations.md)** - Database layer documentation

---

**Note**: This API is part of the dual display library system introduced to replace the simple artist browsing interface with a more sophisticated search and browse experience.