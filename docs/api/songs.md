# Songs API

Complete API documentation for song management endpoints.

## Base URL

```
/api/songs
```

## Endpoints

### List Songs

Get a list of all songs in the library with optional sorting and pagination.

```http
GET /api/songs
```

#### Query Parameters

| Parameter   | Type     | Default      | Description                                    |
|------------|----------|--------------|------------------------------------------------|
| `limit`    | integer  | All songs    | Maximum number of songs to return (1–500)      |
| `offset`   | integer  | 0            | Number of songs to skip (pagination)           |
| `sort_by`  | string   | `date_added` | Field to sort by (`date_added`, `title`, `artist`, `album`, `year`) |
| `direction`| string   | `desc`       | Sort direction (`asc` or `desc`)               |

#### Response

Returns a JSON **array** of song objects:

```json
[
  {
    "id": "uuid-string",
    "title": "Song Title",
    "artist": "Artist Name",
    "album": "Album Name",
    "duration": 245.5,
    "dateAdded": "2026-01-28T10:00:00",
    "source": "youtube",
    "sourceUrl": "https://youtube.com/watch?v=...",
    "videoId": "abc123",
    "year": 2024,
    "albumCoverUrl": "/api/albums/12/cover",
    "plainLyrics": "Lyrics text...",
    "syncedLyrics": "[00:12.00] First line...",
    "engineType": "three_track",
    "artists": [{ "id": 1, "name": "Artist Name", "role": "primary" }],
    "status": "processed"
  }
]
```

---

### Search Songs

Search the library by title, artist, or album, with pagination and optional grouping by artist.

```http
GET /api/songs/search
```

#### Query Parameters

| Parameter         | Type    | Default     | Description                                        |
|-------------------|---------|-------------|----------------------------------------------------|
| `q`               | string  | `""`        | Search query (matches title, artist, album)        |
| `limit`           | integer | 20          | Maximum results (1–100)                            |
| `offset`          | integer | 0           | Results to skip                                    |
| `group_by_artist` | boolean | false       | Group results by artist                            |
| `sort`            | string  | `relevance` | Sort order (`relevance`, `title`, `artist`, `date_added`) |
| `direction`       | string  | `desc`      | Sort direction (`asc` or `desc`)                   |

#### Response (default)

```json
{
  "songs": [ { "id": "uuid-string", "title": "Matching Song", "artist": "Artist Name" } ],
  "pagination": {
    "total": 150,
    "limit": 20,
    "offset": 0,
    "hasMore": true
  }
}
```

#### Response (`group_by_artist=true`)

```json
{
  "artists": [
    {
      "artist": "Artist Name",
      "songCount": 15,
      "songs": [ { "id": "uuid-string", "title": "Song Title" } ]
    }
  ],
  "totalSongs": 42,
  "totalArtists": 3,
  "pagination": { "total": 3, "limit": 20, "offset": 0, "hasMore": false }
}
```

Each grouped artist includes up to 5 of their songs.

---

### List Artists

Get all unique artists with song counts, sorted alphabetically.

```http
GET /api/songs/artists
```

#### Query Parameters

| Parameter | Type    | Default     | Description                              |
|-----------|---------|-------------|------------------------------------------|
| `search`  | string  | —           | Optional search term to filter artists   |
| `limit`   | integer | All artists | Maximum number of artists (1–500)        |
| `offset`  | integer | 0           | Number of artists to skip                |

#### Response

```json
{
  "artists": [
    {
      "id": 1,
      "name": "Artist Name",
      "songCount": 15,
      "firstLetter": "A"
    }
  ],
  "pagination": { "total": 250, "limit": 100, "offset": 0, "hasMore": true }
}
```

Numeric artist names are grouped under `"#"` for `firstLetter`.

---

### Get Songs by Artist

Retrieve all songs for a specific artist with pagination.

```http
GET /api/songs/by-artist/{artist_name}
```

#### Path Parameters

| Parameter     | Type   | Description             |
|---------------|--------|-------------------------|
| `artist_name` | string | URL-encoded artist name |

#### Query Parameters

| Parameter   | Type    | Default | Description                                       |
|-------------|---------|---------|---------------------------------------------------|
| `limit`     | integer | 20      | Songs per page (1–500)                            |
| `offset`    | integer | 0       | Number of songs to skip                           |
| `sort`      | string  | `title` | Sort field (`title`, `album`, `year`, `dateAdded`)|
| `direction` | string  | `asc`   | Sort direction (`asc` or `desc`)                  |

#### Response

```json
{
  "songs": [ { "id": "uuid-string", "title": "Song Title", "album": "Album Name" } ],
  "artist": "Artist Name",
  "pagination": { "total": 15, "limit": 20, "offset": 0, "hasMore": false }
}
```

#### Example Request

```bash
curl "http://localhost:5123/api/songs/by-artist/Queen?limit=50&sort=year&direction=asc"
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
  "dateAdded": "2026-01-28T10:00:00",
  "source": "youtube",
  "sourceUrl": "https://youtube.com/watch?v=...",
  "videoId": "abc123",
  "year": 2024,
  "releaseDate": "2024-03-01",
  "plainLyrics": "Lyrics text...",
  "syncedLyrics": "[00:12.00] First line...",
  "wordSyncedLyrics": null,
  "itunesTrackId": 123456789,
  "itunesExplicit": false,
  "itunesPreviewUrl": "https://...",
  "artistId": 1,
  "albumId": 12,
  "albumCoverUrl": "/api/albums/12/cover",
  "engineType": "three_track",
  "chordsData": null,
  "vocalRangeLow": "G2",
  "vocalRangeHigh": "E5",
  "loudnessDbfs": -11.2,
  "gainDb": -2.8,
  "musicbrainzRecordingId": null,
  "acoustidScore": null,
  "acoustidFingerprintStatus": null,
  "artists": [{ "id": 1, "name": "Artist Name", "role": "primary" }],
  "status": "processed"
}
```

#### Error Responses

- `404 Not Found` — Song with the given ID doesn't exist

---

### Create Song

Create a new song entry (typically called during the upload/processing workflow). Returns `201 Created` and also creates the song's library directory.

```http
POST /api/songs
```

#### Request Body

```json
{
  "id": "optional-uuid",
  "title": "Song Title",
  "artist": "Artist Name",
  "album": "Album Name",
  "duration": 245.5,
  "source": "youtube",
  "video_id": "abc123"
}
```

`title` and `artist` are required; everything else is optional (`id` is generated if omitted).

#### Response

The full song object (see [Get Song Details](#get-song-details)) with `"status": "pending"`.

---

### Update Song

Update song metadata. Only provided fields are changed.

```http
PATCH /api/songs/{song_id}
```

#### Path Parameters

| Parameter | Type   | Description    |
|-----------|--------|----------------|
| `song_id` | string | Song UUID      |

#### Request Body

All fields optional (camelCase):

```json
{
  "title": "Updated Title",
  "artist": "Updated Artist",
  "album": "Updated Album",
  "year": 2024,
  "releaseDate": "2024-03-01",
  "plainLyrics": "New lyrics...",
  "syncedLyrics": "[00:10.00] New synced lyrics...",
  "wordSyncedLyrics": null,
  "itunesTrackId": 123456789,
  "itunesCollectionId": 987654321,
  "itunesArtworkUrls": ["https://..."],
  "itunesExplicit": false,
  "itunesPreviewUrl": "https://...",
  "loudnessDbfs": -11.2,
  "gainDb": -2.8
}
```

Notes:
- Updating `plainLyrics` or `syncedLyrics` clears any existing `wordSyncedLyrics`.
- Providing `itunesCollectionId` links the song to an album (created if needed) and downloads its cover from `itunesArtworkUrls`.

#### Response

The full updated song object (see [Get Song Details](#get-song-details)).

---

### Delete Song

Delete a song and all associated files. **Requires authentication.**

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
  "message": "Song deleted successfully"
}
```

**Note:** This permanently deletes the database record and the song's library directory (original audio, separated tracks, thumbnail).

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
| `track_type` | string | Track type: `vocals`, `instrumental`, `backing-vocals`, or `original` |

#### Response

Binary audio stream (MP3 format)

**Headers:**
- `Content-Type: audio/mpeg`
- `Content-Disposition: attachment; filename="{track_type}.mp3"`

#### Error Responses

- `400 Bad Request` — Invalid track type
- `404 Not Found` — Song or track file not found

---

### Get Song Thumbnail

Get the thumbnail image for a song. Formats are auto-detected in order: WebP, JPEG, PNG.

```http
GET /api/songs/{song_id}/thumbnail
```

#### Path Parameters

| Parameter | Type   | Description    |
|-----------|--------|----------------|
| `song_id` | string | Song UUID      |

#### Response

Binary image data with the matching `Content-Type` (`image/webp`, `image/jpeg`, or `image/png`).

#### Error Responses

- `404 Not Found` — Song or thumbnail not found

---

### Get Song Chords

Get chord detection data for a song.

```http
GET /api/songs/{song_id}/chords
```

#### Response

The song's `chordsData` (or `404` if the song doesn't exist).

---

### Reprocess Song

Re-process a song's audio with a different separation engine. Returns `202 Accepted` with a job ID for tracking progress. **Requires authentication.**

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
  "engine_type": "three_track"
}
```

**Available Engines:**
- `three_track` — Three-stem separation: vocals, backing vocals, instrumental (default)
- `demucs` — Standard Demucs model (fast, balanced)
- `roformer` — Roformer model (slower, higher quality vocals)
- `hybrid` — Multi-stage processing (slowest, best quality)
- `clean_backing` — Advanced 3-stage processing

#### Response

```json
{
  "jobId": "job-uuid",
  "status": "pending",
  "message": "Reprocessing started with three_track"
}
```

#### Error Responses

- `404 Not Found` — Song doesn't exist
- `400 Bad Request` — Original audio file missing
- `409 Conflict` — Song is already being processed

---

## Maintenance & Fingerprinting Endpoints

The songs router also exposes a family of library-maintenance routes that are used by the admin tooling and are best explored via [Swagger UI](../api-reference.md): `GET /library-audit`, `GET /metadata-audit`, `GET /duplicates`, `GET /by-fingerprint-status`, `DELETE /orphan/{dir_name}`, `DELETE /orphan-bulk`, `DELETE /ghost-bulk`, `POST /fingerprint`, `POST /{song_id}/fingerprint`, `POST /{song_id}/fingerprint/lookup`, `POST /{song_id}/fingerprint/apply`, `POST /{song_id}/skip-fingerprint`, `POST /{song_id}/analyze-vocal-range`, `POST /{song_id}/validate-youtube-replacement`, `POST /{song_id}/validate-upload-replacement`, `POST /{song_id}/replace-youtube`, `POST /{song_id}/replace-upload`, `POST /backfill-artwork`, `POST /backfill-duration`, `POST /backfill-vocal-range`.

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
curl "http://localhost:5123/api/songs/search?q=bohemian&limit=20"

# Group search results by artist
curl "http://localhost:5123/api/songs/search?q=queen&group_by_artist=true"

# List all artists
curl http://localhost:5123/api/songs/artists

# Songs by one artist
curl "http://localhost:5123/api/songs/by-artist/Queen?sort=year"

# List recent songs (paginated)
curl "http://localhost:5123/api/songs?limit=20&sort_by=date_added&direction=desc"
```

### Update Metadata

```bash
# Update song details
curl -X PATCH http://localhost:5123/api/songs/abc-123-def \
  -H "Content-Type: application/json" \
  -d '{
    "title": "New Title",
    "year": 2024
  }'
```

---

## Related Documentation

- [Jobs API](jobs.md) - Background processing endpoints
- [Queue API](queue.md) - Karaoke queue management
- [YouTube & Metadata Search API](youtube.md) - Importing songs and metadata search
- [Library API](library.md) - Artists and albums
- [Error Handling Guide](error-handling.md) - Error codes and handling
