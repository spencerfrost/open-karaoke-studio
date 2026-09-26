# YouTube & Metadata Search API

API documentation for finding and importing songs: YouTube video search/download, YouTube Music browsing, and MusicBrainz metadata search.

## Base URLs

```
/api/youtube
/api/youtube-music
/api/musicbrainz
```

---

## YouTube Endpoints

### Search YouTube

```http
GET /api/youtube/search
```

#### Query Parameters

| Parameter    | Type    | Default | Description                  |
|--------------|---------|---------|------------------------------|
| `query`      | string  | —       | Search query (required)      |
| `maxResults` | integer | 10      | Maximum results (1–50)       |

#### Response

```json
{
  "success": true,
  "message": "Found 10 videos matching 'queen bohemian rhapsody'",
  "data": [ { "id": "fJ9rUzIMcZQ", "title": "...", "channel": "...", "duration": 355 } ]
}
```

---

### Preview YouTube Audio

Get a `302` redirect to a direct audio-only stream URL (extracted via yt-dlp), letting the browser stream a preview without downloading.

```http
GET /api/youtube/preview/{video_id}
```

---

### Download & Process

Download a YouTube video's audio and start vocal separation. Returns `202 Accepted` with a job ID; track progress via the [Jobs API](jobs.md) or the jobs WebSocket. **Requires a logged-in account or active session membership.** Demo sessions are subject to download quotas (`429` when exceeded).

```http
POST /api/youtube/download
```

#### Request Body

```json
{
  "video_id": "fJ9rUzIMcZQ",
  "song_id": "song-uuid",
  "title": "Bohemian Rhapsody",
  "artist": "Queen",
  "album": "A Night at the Opera",
  "engine_type": "three_track"
}
```

`video_id` and `song_id` are required (create the song first via `POST /api/songs`). `engine_type` is one of `three_track` (default), `demucs`, `roformer`, `hybrid`, `clean_backing`, `three_track_duality_v2`, `three_track_mel1143`.

#### Response

```json
{
  "success": true,
  "message": "YouTube processing started",
  "data": {
    "jobId": "job-uuid",
    "status": "pending",
    "message": "YouTube processing job created"
  }
}
```

---

## YouTube Music Endpoints

Richer music-oriented search used by the Add Song flow. Song results include an `existsInLibrary` flag.

### Search

```http
GET /api/youtube-music/search?q={query}&limit=10
```

#### Response

```json
{
  "artists": [ { "browseId": "UC...", "artist": "Queen", "thumbnails": [] } ],
  "songs": [
    {
      "videoId": "fJ9rUzIMcZQ",
      "title": "Bohemian Rhapsody",
      "artist": "Queen",
      "album": "A Night at the Opera",
      "duration": "5:55",
      "existsInLibrary": true
    }
  ],
  "error": null
}
```

### Artist Details

Get artist info with top songs (with `existsInLibrary` flags) and albums.

```http
GET /api/youtube-music/artist/{artist_id}?limit=12
```

### Artist Releases (Load More)

Fetch all albums or singles when the initial artist response includes `albumsMore`/`singlesMore` pagination metadata.

```http
GET /api/youtube-music/artist/{artist_id}/releases?channel_id={channel_id}&params={params}
```

### Album Tracks

```http
GET /api/youtube-music/album/{album_id}/tracks
```

Returns the album track list with `existsInLibrary` flags.

---

## MusicBrainz Endpoints

### Search Recordings

Free-text search of MusicBrainz recordings, used for metadata correction. **Requires authentication.**

```http
GET /api/musicbrainz/search?query={query}&limit=10
```

#### Response

```json
{
  "results": [
    {
      "score": 100,
      "recordingId": "mbid-uuid",
      "title": "Bohemian Rhapsody",
      "artist": "Queen",
      "primaryArtist": "Queen",
      "featuredArtists": [],
      "album": "A Night at the Opera",
      "duration": 355,
      "releaseDate": "1975-11-21"
    }
  ]
}
```

Returns `502` if the MusicBrainz API is unreachable.

---

## Typical Import Flow

```bash
# 1. Search YouTube Music
curl "http://localhost:5123/api/youtube-music/search?q=queen+bohemian+rhapsody"

# 2. Preview the audio before committing
curl -L "http://localhost:5123/api/youtube/preview/fJ9rUzIMcZQ" -o preview.m4a

# 3. Create the song record
curl -X POST http://localhost:5123/api/songs \
  -H "Content-Type: application/json" \
  -d '{"title": "Bohemian Rhapsody", "artist": "Queen", "video_id": "fJ9rUzIMcZQ"}'

# 4. Download and process (as a session member or logged-in user)
curl -X POST http://localhost:5123/api/youtube/download \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: {session_id}" -H "X-Device-ID: {device_id}" \
  -d '{"video_id": "fJ9rUzIMcZQ", "song_id": "{song_id}", "title": "Bohemian Rhapsody", "artist": "Queen"}'

# 5. Watch progress via the jobs WebSocket or poll the job
```

---

## Related Documentation

- [Songs API](songs.md) - Creating song records and applying metadata
- [Jobs API](jobs.md) - Tracking download/processing jobs
- [Sessions API](sessions.md) - Session membership for guest downloads
