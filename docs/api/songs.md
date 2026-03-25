# Songs API

Complete API documentation for song management endpoints.

## Base URL

```
/api/songs
```

## Endpoints

### List Songs

Get a list of all songs in the library with optional filtering and pagination.

```http
GET /api/songs
```

#### Query Parameters

| Parameter   | Type     | Default      | Description                                    |
|------------|----------|--------------|------------------------------------------------|
| `limit`    | integer  | All songs    | Maximum number of songs to return              |
| `offset`   | integer  | 0            | Number of songs to skip (pagination)           |
| `sort_by`  | string   | `date_added` | Field to sort by (`date_added`, `title`, `artist`, `album`, `year`) |
| `direction`| string   | `desc`       | Sort direction (`asc` or `desc`)               |

#### Response

```json
{
  "songs": [
    {
      "id": "uuid-string",
      "title": "Song Title",
      "artist": "Artist Name",
      "album": "Album Name",
      "duration": 245.5,
      "date_added": "2026-01-28T10:00:00",
      "source": "youtube",
      "source_url": "https://youtube.com/watch?v=...",
      "vocals_path": "uuid/vocals.mp3",
      "instrumental_path": "uuid/instrumental.mp3",
      "original_path": "uuid/original.mp3",
      "thumbnail_path": "uuid/thumbnail.jpg",
      "bpm": 120.0,
      "year": 2024,
      "genre": "Pop",
      "plain_lyrics": "Lyrics text...",
      "synced_lyrics": "[00:12.00] First line..."
    }
  ],
  "total": 150
}
```

---

### Get Song Details

Get detailed information about a specific song.

```http
GET /api/songs/{song_id}
```

#### Path Parameters

| Parameter | Type   | Description    |
|-----------|--------|----------------|
| `song_id` | string | Song UUID      |

#### Response

```json
{
  "id": "uuid-string",
  "title": "Song Title",
  "artist": "Artist Name",
  "album": "Album Name",
  "duration": 245.5,
  "date_added": "2026-01-28T10:00:00",
  "vocals_path": "uuid/vocals.mp3",
  "instrumental_path": "uuid/instrumental.mp3",
  "original_path": "uuid/original.mp3",
  "thumbnail_path": "uuid/thumbnail.jpg",
  "source": "youtube",
  "video_id": "abc123",
  "bpm": 120.0,
  "year": 2024,
  "genre": "Pop",
  "itunes_track_id": 123456789,
  "itunes_artwork_urls": ["https://..."],
  "youtube_thumbnail_urls": ["https://..."],
  "plain_lyrics": "Lyrics text...",
  "synced_lyrics": "[00:12.00] First line...",
  "engine_type": "demucs"
}
```

#### Error Responses

- `404 Not Found` - Song with the given ID doesn't exist

```json
{
  "error": "Song not found",
  "code": "RESOURCE_NOT_FOUND",
  "details": {
    "resource_type": "Song",
    "resource_id": "uuid-string"
  }
}
```

---

### Create Song

Create a new song entry (typically called during upload/processing workflow).

```http
POST /api/songs
```

#### Request Body

```json
{
  "title": "Song Title",
  "artist": "Artist Name",
  "album": "Album Name",
  "duration": 245.5,
  "source": "youtube",
  "source_url": "https://youtube.com/watch?v=...",
  "video_id": "abc123",
  "year": 2024,
  "genre": "Pop"
}
```

#### Response

```json
{
  "id": "uuid-string",
  "title": "Song Title",
  "artist": "Artist Name",
  "status": "processing"
}
```

---

### Update Song

Update song metadata.

```http
PUT /api/songs/{song_id}
```

#### Path Parameters

| Parameter | Type   | Description    |
|-----------|--------|----------------|
| `song_id` | string | Song UUID      |

#### Request Body

All fields are optional. Only provided fields will be updated.

```json
{
  "title": "Updated Title",
  "artist": "Updated Artist",
  "album": "Updated Album",
  "year": 2024,
  "genre": "Rock",
  "bpm": 125.0,
  "plain_lyrics": "New lyrics...",
  "synced_lyrics": "[00:10.00] New synced lyrics..."
}
```

#### Response

```json
{
  "id": "uuid-string",
  "title": "Updated Title",
  "artist": "Updated Artist",
  "message": "Song updated successfully"
}
```

---

### Delete Song

Delete a song and all associated files.

```http
DELETE /api/songs/{song_id}
```

#### Path Parameters

| Parameter | Type   | Description    |
|-----------|--------|----------------|
| `song_id` | string | Song UUID      |

#### Response

```json
{
  "message": "Song deleted successfully",
  "song_id": "uuid-string"
}
```

**Note:** This will permanently delete:
- Original audio file
- Vocals track
- Instrumental track
- Thumbnail image
- Database record
- Associated lyrics

---

### Stream Audio Track

Stream a specific audio track for a song.

```http
GET /api/songs/{song_id}/download/{track_type}
```

#### Path Parameters

| Parameter    | Type   | Description                                     |
|--------------|--------|-------------------------------------------------|
| `song_id`    | string | Song UUID                                       |
| `track_type` | string | Track type: `vocals`, `instrumental`, or `original` |

#### Response

Binary audio stream (MP3 format)

**Headers:**
- `Content-Type: audio/mpeg`
- `Content-Disposition: attachment; filename="{track_type}.mp3"`

#### Error Responses

- `400 Bad Request` - Invalid track type
- `404 Not Found` - Song or file not found

```json
{
  "error": "Invalid track type",
  "code": "INVALID_TRACK_TYPE",
  "details": {
    "track_type": "unknown",
    "valid_types": ["vocals", "instrumental", "original"]
  }
}
```

---

### Get Song Thumbnail

Get the thumbnail image for a song.

```http
GET /api/songs/{song_id}/thumbnail
```

#### Path Parameters

| Parameter | Type   | Description    |
|-----------|--------|----------------|
| `song_id` | string | Song UUID      |

#### Response

Binary image data (JPEG/PNG format)

**Headers:**
- `Content-Type: image/jpeg` or `image/png`

#### Error Responses

- `404 Not Found` - Thumbnail not found

---

### Search Songs

Search for songs by title, artist, or album.

```http
GET /api/songs/search
```

#### Query Parameters

| Parameter   | Type   | Required | Description                              |
|------------|--------|----------|------------------------------------------|
| `q`        | string | Yes      | Search query                             |
| `filter_by`| string | No       | Filter by field (`artist`, `title`, `album`) |

#### Response

```json
{
  "songs": [
    {
      "id": "uuid-string",
      "title": "Matching Song",
      "artist": "Artist Name",
      "album": "Album Name",
      "duration": 180.0
    }
  ],
  "total": 5,
  "query": "search term"
}
```

---

### List Artists

Get a list of all artists in the library with song counts.

```http
GET /api/songs/artists
```

#### Response

```json
{
  "artists": [
    {
      "name": "Artist Name",
      "song_count": 15,
      "songs": [
        {
          "id": "uuid-string",
          "title": "Song Title",
          "album": "Album Name",
          "duration": 200.0
        }
      ]
    }
  ],
  "total_artists": 50
}
```

---

### Reprocess Song

Reprocess a song's audio with a different separation engine.

```http
POST /api/songs/{song_id}/reprocess
```

#### Path Parameters

| Parameter | Type   | Description    |
|-----------|--------|----------------|
| `song_id` | string | Song UUID      |

#### Request Body

```json
{
  "engine_type": "roformer"
}
```

**Available Engines:**
- `demucs` - Standard Demucs model (fast, balanced)
- `roformer` - Roformer model (slower, higher quality vocals)
- `hybrid` - Multi-stage processing (slowest, best quality)
- `clean_backing` - Advanced 3-stage processing

#### Response

```json
{
  "message": "Reprocessing started",
  "job_id": "job-uuid",
  "song_id": "uuid-string"
}
```

---

### Auto-Save iTunes Metadata

Automatically fetch and save iTunes metadata for a song.

```http
POST /api/songs/metadata/auto
```

#### Request Body

```json
{
  "song_id": "uuid-string",
  "itunes_track_id": 123456789,
  "title": "Song Title",
  "artist": "Artist Name",
  "album": "Album Name",
  "artwork_url": "https://...",
  "year": 2024,
  "genre": "Pop",
  "preview_url": "https://...",
  "explicit": false
}
```

#### Response

```json
{
  "message": "Metadata saved successfully",
  "song_id": "uuid-string"
}
```

---

## Common Error Codes

| Error Code              | HTTP Status | Description                |
|------------------------|-------------|----------------------------|
| `RESOURCE_NOT_FOUND`   | 404         | Song doesn't exist         |
| `INVALID_TRACK_TYPE`   | 400         | Invalid audio track type   |
| `FILE_NOT_FOUND`       | 404         | Audio file missing         |
| `FILE_OPERATION_ERROR` | 500         | File system error          |
| `DATABASE_ERROR`       | 500         | Database operation failed  |
| `VALIDATION_ERROR`     | 400         | Invalid request data       |

---

## Usage Examples

### Fetch and Stream a Song

```bash
# Get song details
curl http://localhost:5123/api/songs/abc-123-def

# Stream vocals track
curl http://localhost:5123/api/songs/abc-123-def/download/vocals \
  --output vocals.mp3

# Get thumbnail
curl http://localhost:5123/api/songs/abc-123-def/thumbnail \
  --output thumbnail.jpg
```

### Search and List

```bash
# Search for songs
curl "http://localhost:5123/api/songs/search?q=artist+name"

# List all artists
curl http://localhost:5123/api/songs/artists

# List recent songs (paginated)
curl "http://localhost:5123/api/songs?limit=20&sort_by=date_added&direction=desc"
```

### Update Metadata

```bash
# Update song details
curl -X PUT http://localhost:5123/api/songs/abc-123-def \
  -H "Content-Type: application/json" \
  -d '{
    "title": "New Title",
    "bpm": 128.0,
    "genre": "Electronic"
  }'
```

---

## Related Documentation

- [Jobs API](jobs.md) - Background processing endpoints
- [Queue API](queue.md) - Karaoke queue management
- [Metadata API](metadata.md) - External metadata search
- [Error Handling Guide](error-handling.md) - Error codes and handling
