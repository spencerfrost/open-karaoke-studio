# Metadata API

Complete API documentation for external metadata search and enrichment.

## Base URL

```
/api/metadata
```

## Overview

The Metadata API provides access to external music metadata services for enriching song information. Currently supports iTunes Search API for fetching album artwork, genre information, and other metadata.

---

## Endpoints

### Search iTunes

Search for song metadata using the iTunes Search API.

```http
GET /api/metadata/search
```

#### Query Parameters

| Parameter | Type   | Required | Description                           |
|----------|--------|----------|---------------------------------------|
| `term`   | string | Yes      | Search query (artist, song, or album) |
| `entity` | string | No       | Entity type (default: `song`)         |
| `limit`  | integer| No       | Maximum results (default: 25)         |

**Valid Entity Types:**
- `song` (default)
- `album`
- `musicArtist`

#### Response

```json
{
  "resultCount": 5,
  "results": [
    {
      "trackId": 123456789,
      "trackName": "Song Title",
      "artistName": "Artist Name",
      "collectionName": "Album Name",
      "primaryGenreName": "Pop",
      "releaseDate": "2024-01-15T08:00:00Z",
      "trackTimeMillis": 245500,
      "trackNumber": 5,
      "trackCount": 12,
      "discNumber": 1,
      "isStreamable": true,
      "artworkUrl30": "https://...",
      "artworkUrl60": "https://...",
      "artworkUrl100": "https://...",
      "previewUrl": "https://audio-ssl.itunes.apple.com/...",
      "trackExplicitness": "notExplicit",
      "collectionExplicitness": "notExplicit",
      "country": "USA",
      "currency": "USD",
      "trackPrice": 1.29,
      "collectionPrice": 9.99
    }
  ]
}
```

#### iTunes Artwork URLs

The API returns multiple artwork resolutions:
- `artworkUrl30`: 30x30px thumbnail
- `artworkUrl60`: 60x60px thumbnail
- `artworkUrl100`: 100x100px album art

**Higher Resolution Artwork:**
You can modify the URL to get higher resolution artwork:
```
# Original
https://is1-ssl.mzstatic.com/image/.../100x100bb.jpg

# High Resolution (replace dimensions)
https://is1-ssl.mzstatic.com/image/.../600x600bb.jpg
https://is1-ssl.mzstatic.com/image/.../1000x1000bb.jpg
```

---

### Get Artwork

Get high-resolution artwork URL for a song.

```http
GET /api/metadata/artwork
```

#### Query Parameters

| Parameter    | Type    | Required | Description                    |
|-------------|---------|----------|--------------------------------|
| `track_id`  | integer | Yes      | iTunes track ID                |
| `resolution`| integer | No       | Desired resolution (default: 600) |

**Common Resolutions:**
- `100` - Small thumbnail
- `300` - Medium
- `600` - High quality (default)
- `1000` - Very high quality
- `1200` - Maximum quality

#### Response

```json
{
  "artwork_url": "https://is1-ssl.mzstatic.com/image/.../600x600bb.jpg",
  "resolution": 600,
  "track_id": 123456789
}
```

---

## iTunes Metadata Fields

### Complete Field Reference

| Field                  | Type    | Description                              |
|-----------------------|---------|------------------------------------------|
| `trackId`             | integer | Unique iTunes track identifier           |
| `trackName`           | string  | Song title                               |
| `artistName`          | string  | Artist name                              |
| `collectionName`      | string  | Album name                               |
| `primaryGenreName`    | string  | Primary music genre                      |
| `releaseDate`         | string  | Release date (ISO 8601)                  |
| `trackTimeMillis`     | integer | Duration in milliseconds                 |
| `trackNumber`         | integer | Track position on album                  |
| `trackCount`          | integer | Total tracks on album                    |
| `discNumber`          | integer | Disc number (multi-disc albums)          |
| `discCount`           | integer | Total discs in album                     |
| `trackExplicitness`   | string  | `explicit`, `cleaned`, or `notExplicit`  |
| `isStreamable`        | boolean | Whether track is streamable              |
| `previewUrl`          | string  | 30-second preview MP3 URL                |
| `artworkUrl30`        | string  | 30x30px artwork                          |
| `artworkUrl60`        | string  | 60x60px artwork                          |
| `artworkUrl100`       | string  | 100x100px artwork                        |
| `country`             | string  | Country code                             |
| `currency`            | string  | Currency code                            |
| `trackPrice`          | number  | Track price                              |
| `collectionPrice`     | number  | Album price                              |

---

## Genre Classification

iTunes uses standardized genre names for music classification.

### Common Genres

| Genre               | Description                          |
|--------------------|--------------------------------------|
| `Pop`              | Popular music                        |
| `Rock`             | Rock music                           |
| `Alternative`      | Alternative rock                     |
| `Hip-Hop/Rap`      | Hip-hop and rap                      |
| `R&B/Soul`         | Rhythm and blues, soul               |
| `Electronic`       | Electronic dance music               |
| `Country`          | Country music                        |
| `Dance`            | Dance music                          |
| `Jazz`             | Jazz music                           |
| `Classical`        | Classical music                      |
| `Metal`            | Heavy metal                          |
| `Indie`            | Independent music                    |
| `Folk`             | Folk music                           |
| `Reggae`           | Reggae music                         |
| `Blues`            | Blues music                          |

---

## Preview Audio

iTunes provides 30-second preview clips for songs.

### Preview URL Format

```
https://audio-ssl.itunes.apple.com/itunes-assets/AudioPreview{...}/v4/{...}.m4a
```

**Usage:**
```html
<audio controls>
  <source src="https://audio-ssl.itunes.apple.com/..." type="audio/mp4">
</audio>
```

**Notes:**
- Previews are **30 seconds long**
- Format: **M4A (AAC audio)**
- Used for song verification before selection

---

## Error Codes

| Error Code                  | HTTP Status | Description                      |
|----------------------------|-------------|----------------------------------|
| `VALIDATION_ERROR`         | 400         | Missing or invalid parameters    |
| `METADATA_CONNECTION_ERROR`| 502         | iTunes API unreachable           |
| `NETWORK_ERROR`            | 502         | Network connection failed        |
| `SERVICE_ERROR`            | 500         | Internal metadata service error  |

---

## Usage Examples

### Basic Search

```bash
# Search for a song
curl "http://localhost:5123/api/metadata/search?term=artist+song+name&entity=song&limit=10"

# Search for an artist
curl "http://localhost:5123/api/metadata/search?term=taylor+swift&entity=musicArtist"

# Search for an album
curl "http://localhost:5123/api/metadata/search?term=1989&entity=album"
```

### Get High-Res Artwork

```bash
# Get 600x600 artwork (default)
curl "http://localhost:5123/api/metadata/artwork?track_id=123456789"

# Get 1200x1200 artwork (maximum quality)
curl "http://localhost:5123/api/metadata/artwork?track_id=123456789&resolution=1200"
```

### Integration Example (JavaScript)

```javascript
// Search iTunes
async function searchItunes(query) {
  const response = await fetch(
    `http://localhost:5123/api/metadata/search?term=${encodeURIComponent(query)}&limit=5`
  );
  const data = await response.json();
  return data.results;
}

// Get song metadata
async function getSongMetadata(artist, title) {
  const results = await searchItunes(`${artist} ${title}`);
  
  if (results.length > 0) {
    const track = results[0];
    
    return {
      title: track.trackName,
      artist: track.artistName,
      album: track.collectionName,
      genre: track.primaryGenreName,
      year: new Date(track.releaseDate).getFullYear(),
      duration: track.trackTimeMillis / 1000,
      artwork: track.artworkUrl100.replace('100x100bb', '600x600bb'),
      preview: track.previewUrl,
      explicit: track.trackExplicitness === 'explicit'
    };
  }
  
  return null;
}

// Play preview
async function playPreview(previewUrl) {
  const audio = new Audio(previewUrl);
  await audio.play();
  
  // Stop after 30 seconds
  setTimeout(() => audio.pause(), 30000);
}
```

---

## Metadata Enrichment Workflow

### Typical Use Case

1. **User Adds Song:**
   - User uploads or selects a YouTube video
   - Basic metadata extracted (title, artist from filename/title)

2. **Search iTunes:**
   - App calls `/api/metadata/search` with artist + title
   - iTunes returns comprehensive metadata

3. **Display Options:**
   - Show multiple matches to user
   - Display artwork previews
   - Play 30-second previews

4. **User Selects:**
   - User confirms correct match
   - App saves iTunes metadata to song record

5. **Enhanced Song:**
   - Song now has:
     - High-quality artwork
     - Accurate genre/year
     - Album information
     - iTunes track ID for future reference

---

## Rate Limiting

iTunes Search API has rate limits:
- **20 requests per minute** per IP address
- **200 requests per hour** per IP address

**Best Practices:**
- Cache results when possible
- Debounce search queries
- Use reasonable limits (don't fetch 100 results)

---

## Alternative Metadata Sources

While iTunes is the primary source, the architecture supports adding additional providers:

### Potential Future Sources

- **MusicBrainz** - Open music database
- **Spotify API** - Streaming service metadata
- **Last.fm** - Music metadata and tags
- **Discogs** - Music database with detailed info

---

## Related Documentation

- [Songs API](songs.md) - Song metadata endpoints
- [Architecture: Metadata Service](../ARCHITECTURE.md#metadata--search) - Service architecture
- [Features: Metadata Search](../FEATURES.md#itunes-metadata-search) - Feature details
- [Error Handling Guide](error-handling.md) - Error codes and handling

---

## External Resources

- [iTunes Search API Documentation](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/)
- [iTunes Genre IDs](https://affiliate.itunes.apple.com/resources/documentation/genre-mapping/)
