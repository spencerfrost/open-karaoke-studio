# Songs API

Complete API documentation for song management endpoints.

## Base URL

```
/api/songs
```

## Access

Every read here — list, search, artists, shows, by-artist, by-show and song details — needs an
account or a session-member credential (see [Authentication](authentication.md)). The media
URLs (`/thumbnail`, `/download/{track_type}`, album covers, artist images) don't: `<img>` and
`<audio>` can't send headers. A song's id is a random UUID, and you only learn one through the
authenticated reads. The library-maintenance routes listed at the end are admin-only.

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
    "videoIsAlbumArt": true,
    "year": 2024,
    "albumCoverUrl": "/api/albums/12/cover",
    "plainLyrics": "Lyrics text...",
    "syncedLyrics": "[00:12.00] First line...",
    "engineType": "three_track",
    "artists": [{ "id": 1, "name": "Artist Name", "role": "primary", "creditedAs": "Artist Name" }],
    "status": "processed"
  }
]
```

---

### Search Songs

Search the library by title, artist, album or show, with pagination and optional grouping by artist. The artist part also matches every credited artist under any name they go by (an alias, or the name a recording credits them as), so "Dixie Chicks" finds The Chicks and a guest's name finds the songs they're featured on.

```http
GET /api/songs/search
```

#### Query Parameters

| Parameter         | Type    | Default     | Description                                        |
|-------------------|---------|-------------|----------------------------------------------------|
| `q`               | string  | `""`        | Search query (matches title, artist, album, show, credited artists) |
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

Songs are grouped by their primary artist, so "JAY-Z" and "Jay-Z feat. X" land together. Each grouped artist includes up to 5 of their matching songs.

---

### List Artists

The artist list, sorted alphabetically. It lists an artist with at least one song of their own, or who is featured on songs by two or more different artists. A guest on one artist's songs isn't listed: their songs file under that artist. A `search` finds every artist, by name or alias, listed or not.

```http
GET /api/songs/artists
```

#### Query Parameters

| Parameter | Type    | Default     | Description                              |
|-----------|---------|-------------|------------------------------------------|
| `search`  | string  | —           | Optional search term; matches names and aliases, and includes unlisted artists |
| `limit`   | integer | All artists | Maximum number of artists (1–500)        |
| `offset`  | integer | 0           | Number of artists to skip                |

#### Response

```json
{
  "artists": [
    {
      "id": 1,
      "name": "Artist Name",
      "sortName": "artist name",
      "ownCount": 15,
      "featuredCount": 2,
      "firstLetter": "A",
      "youtubeMusicArtistId": "UCiMhD4jzUqG-IgPzUmmytRQ",
      "listed": true
    }
  ],
  "pagination": { "total": 250, "limit": 100, "offset": 0, "hasMore": true }
}
```

`ownCount` counts songs they're the primary artist on, `featuredCount` the ones they're featured on. `listed` says whether the full list (no `search`) has them. `youtubeMusicArtistId` is their YouTube Music channel, when a song was added from search. Numeric artist names are grouped under `"#"` for `firstLetter`.

---

### Get Songs by Artist

An artist's songs, with pagination: their own first, then the ones they're featured on. `404` for an unknown artist.

```http
GET /api/songs/by-artist/{artist_id}
```

#### Path Parameters

| Parameter   | Type    | Description     |
|-------------|---------|-----------------|
| `artist_id` | integer | The artist's id |

#### Query Parameters

| Parameter   | Type    | Default | Description                                       |
|-------------|---------|---------|---------------------------------------------------|
| `limit`     | integer | 20      | Songs per page (1–500)                            |
| `offset`    | integer | 0       | Number of songs to skip                           |
| `sort`      | string  | `title` | Sort field within each group (`title`, `album`, `year`, `dateAdded`)|
| `direction` | string  | `asc`   | Sort direction (`asc` or `desc`)                  |

#### Response

```json
{
  "songs": [ { "id": "uuid-string", "title": "Song Title", "album": "Album Name", "role": "primary" } ],
  "artist": { "id": 1, "name": "Artist Name", "youtubeMusicArtistId": null },
  "pagination": { "total": 15, "limit": 20, "offset": 0, "hasMore": false }
}
```

#### Example Request

```bash
curl "http://localhost:5123/api/songs/by-artist/42?limit=50&sort=year&direction=asc"
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
  "videoIsAlbumArt": true,
  "year": 2024,
  "releaseDate": "2024-03-01",
  "plainLyrics": "Lyrics text...",
  "syncedLyrics": "[00:12.00] First line...",
  "wordSyncedLyrics": null,
  "explicit": false,
  "albumHandSet": false,
  "artistId": 1,
  "albumId": 12,
  "albumCoverUrl": "/api/albums/12/cover",
  "engineType": "three_track",
  "chordsData": null,
  "vocalRangeLow": "G2",
  "vocalRangeHigh": "E5",
  "loudnessLufs": -11.2,
  "truePeakDbtp": -0.4,
  "gainDb": -4.8,
  "musicbrainzRecordingId": null,
  "acoustidScore": null,
  "acoustidFingerprintStatus": null,
  "acoustidSuggestion": null,
  "metadataConfirmed": false,
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

### Add Song from YouTube

Add a YouTube or YouTube Music song to the library and queue its download and processing, in one request. This is what the Add Song page calls. Returns `202 Accepted`. **Requires a logged-in account or active session membership.**

```http
POST /api/songs/from-youtube
```

#### Request Body

```json
{
  "video_id": "HgzGwKwLmgM",
  "title": "Don't Stop Me Now",
  "artists": [{ "name": "Queen", "id": "UCiMhD4jzUqG-IgPzUmmytRQ" }],
  "album": "Jazz",
  "duration": 210,
  "source": "youtube_music"
}
```

`video_id`, `title` and `artists` (at least one, primary first; `id` is the YouTube Music channel and optional) are required. The song is credited from the list as given, first primary and the rest featured, and stores it as one artist line: JAY-Z and Alicia Keys become `"JAY-Z feat. Alicia Keys"`. Channel ids are kept only for `youtube_music`. `source` is `youtube_music` (default) or `youtube`.

In one request it:

1. checks the demo download quota (`429`, or `403` for an ended demo session);
2. looks for the song in the library, by video id or the same artist and title;
3. restarts the song's failed copy if that's the only one, from this video;
4. otherwise creates the song and queues its download;
5. broadcasts the new job on the jobs WebSocket.

#### Response

```json
{ "songId": "song-uuid", "jobId": "job-uuid", "restarted": false }
```

`restarted` is `true` when a failed copy was restarted instead of a song added.

#### Error Responses

- `409` – A working copy (processed or processing) is already in the library, or the failed copy is already being processed
- `422` – Missing `video_id`, `title` or artists
- `429` / `403` – Demo download quota

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
  "artists": [
    { "name": "Chase & Status", "role": "primary" },
    { "name": "Popcaan", "role": "featured" }
  ],
  "album": "Updated Album",
  "year": 2024,
  "releaseDate": "2024-03-01",
  "plainLyrics": "New lyrics...",
  "syncedLyrics": "[00:10.00] New synced lyrics...",
  "wordSyncedLyrics": null,
  "loudnessDbfs": -11.2,
  "gainDb": -2.8
}
```

Notes:
- `artists` is the credit list, with at least one `primary`. When it's sent, the credits are written as given, `artist` is ignored and rebuilt from the list (`"A & B feat. C"`), and the song is confirmed; its MusicBrainz recording stays linked.
- A changed `artist` (or `title`) confirms the song and unlinks its recording. A changed `artist` alone re-credits the song from the text: guests after "feat." split on ",", "&", "and" and "with".
- Updating `plainLyrics` or `syncedLyrics` clears any existing `wordSyncedLyrics`.
- A new `album` name marks the album hand-set: automatic album lookups skip the song, and its cover stays linked. An empty `album` clears the name, the cover link and the marker, so the next lookup finds one.

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

The songs router also exposes a family of library-maintenance routes that are used by the admin tooling and are best explored via [Swagger UI](../api-reference.md): `GET /library-audit`, `GET /metadata-audit`, `GET /duplicates`, `GET /by-fingerprint-status`, `DELETE /orphan/{dir_name}`, `DELETE /orphan-bulk`, `DELETE /ghost-bulk`, `POST /{song_id}/fingerprint`, `POST /{song_id}/fingerprint/lookup`, `POST /{song_id}/fingerprint/apply`, `POST /{song_id}/fingerprint/suggestion/accept`, `POST /{song_id}/skip-fingerprint`, `POST /{song_id}/analyze-vocal-range`, `POST /{song_id}/validate-youtube-replacement`, `POST /{song_id}/validate-upload-replacement`, `POST /{song_id}/replace-youtube`, `POST /{song_id}/replace-upload`. Library-wide backfills (duration, loudness, vocal range, albums and covers, fingerprints) run as batch jobs: see [Admin API](admin.md).

### AcoustID never renames a song

Fingerprinting (on every new or replaced song, the single-song button and the batch job) links the MusicBrainz recording; it never writes `title` or `artist`. `acoustidFingerprintStatus` says what it found:

| Status | Meaning |
|---|---|
| `matched` | A recording agreeing with the title and artist is linked (case, punctuation, bracketed parts and "feat." don't count as differences), or a person picked it |
| `suggested` | A confident (≥ 0.9) recording that names the song differently. Nothing is linked; `acoustidSuggestion` (`recordingId`, `title`, `artist`) waits for review on the admin AcoustID page |
| `ambiguous` | Several recordings tied, none named like the song, and the album didn't narrow them to one |
| `no_match` | AcoustID knows no recording, or only a weak one that names the song differently |
| `failed` | The lookup itself failed |
| `skipped` | A person kept the current title and artist |

`metadataConfirmed` is true once a person has set the song's title or artist: applying a recording (`/fingerprint/apply`, from AcoustID or a MusicBrainz search), accepting a suggestion (`/fingerprint/suggestion/accept`), keeping the current names (`/skip-fingerprint`), or a `PATCH` that changes `title` or `artist`. That `PATCH` also unlinks the old recording. Fingerprinting a confirmed song only links a recording when it has none and the recording agrees; automatic credit runs leave its artist credits alone.

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
