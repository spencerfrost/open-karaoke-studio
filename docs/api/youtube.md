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
  "data": [
    {
      "id": "fJ9rUzIMcZQ",
      "title": "...",
      "channel": "...",
      "duration": 355,
      "library": null
    }
  ]
}
```

Each video carries a `library` field, the same as on [YouTube Music results](#the-library-field), with the channel standing in for the artist.

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

`video_id` and `song_id` are required (create the song first via `POST /api/songs`). To add a song in one request, use [`POST /api/songs/from-youtube`](songs.md#add-song-from-youtube) instead. `engine_type` is one of `three_track` (default), `demucs`, `roformer`, `hybrid`, `clean_backing`, `three_track_duality_v2`, `three_track_mel1143`.

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

Music-oriented search and browse, used by the Add Song flow. Each needs an account or session-member credential, and each is rate limited per client IP (suggestions `120/minute`, the rest `30/minute`). When YouTube Music fails they return `502`; an unknown artist or album is `404`.

### Song Shape

Every song (in search results, an artist's popular songs and album tracks) has the same fields:

```json
{
  "videoId": "HgzGwKwLmgM",
  "title": "Don't Stop Me Now",
  "artists": [{ "name": "Queen", "id": "UCiMhD4jzUqG-IgPzUmmytRQ" }],
  "artist": "Queen",
  "album": "Jazz (Deluxe Edition)",
  "albumId": "MPREb_...",
  "durationSeconds": 210,
  "isExplicit": false,
  "thumbnails": [{ "url": "https://...", "width": 120, "height": 120 }],
  "trackNumber": null,
  "library": { "status": "ready", "songId": "song-uuid" }
}
```

- `artists` keeps every credited artist; `artist` is the same names as the one credit line a library song stores ("JAY-Z feat. Alicia Keys").
- `videoId` is `null` for a track YouTube Music can't play.
- `trackNumber` is set on album tracks only.

#### The `library` field

What the library already holds of this song. A library song matches when it has the same video id, or the same artist and title (case-insensitive).

| Value | Meaning |
|---|---|
| `{"status": "ready", "songId": ...}` | A processed copy exists |
| `{"status": "processing", "songId": ...}` | A copy is still being processed |
| `{"status": "failed", "songId": ...}` | The only copy failed; adding the song restarts it |
| `null` | Not in the library |

A working copy wins over a failed one, and a video id match wins over an artist and title match.

### Search

```http
GET /api/youtube-music/search?q={query}&limit=20
```

`limit` (1–50, default 20) is the number of songs YouTube Music is asked for.

#### Response

```json
{
  "bestMatch": { "...": "a song" },
  "otherVersions": [ { "...": "songs" } ],
  "otherSongs": [ { "...": "songs" } ],
  "artists": [ { "browseId": "UC...", "name": "Queen", "subscribers": "19.1M", "thumbnails": [] } ],
  "topArtistId": "UC..."
}
```

- `bestMatch` is YouTube Music's first song result, which is the original recording in practice. `null` when nothing matched.
- `otherVersions` are the results with the same song title as the best match, ignoring "feat." credits, bracketed notes and a " - Live" style suffix: covers, live takes, remasters.
- `otherSongs` is everything else.
- `artists` holds up to 3.
- `topArtistId` is set when YouTube Music's own top result for the query is an artist ("queen"), and `null` otherwise ("bohemian rhapsody", though an artist by that name exists). The add flow opens that artist when the query was a picked suggestion.

### Suggestions

Search suggestions for a partly typed query.

```http
GET /api/youtube-music/suggestions?q={text}
```

Returns a list of strings, e.g. `["don't stop believing", "don't stop me now"]`.

### Artist Details

The artist, their first 5 popular songs, and every album, single and remix.

```http
GET /api/youtube-music/artist/{artist_id}
```

```json
{
  "artist": { "id": "UC...", "name": "Queen", "thumbnails": [], "description": "...", "subscribers": "19.1M" },
  "topSongs": [ { "...": "songs" } ],
  "hasMoreSongs": true,
  "albums": [ { "browseId": "MPREb_...", "title": "Jazz", "year": "1978", "type": "album", "thumbnails": [] } ],
  "singles": [],
  "remixes": []
}
```

`hasMoreSongs` says the next endpoint has more than these five. `albums` and `singles` are every one, not just the few the artist page lists: oldest first, one per title (YouTube Music can list one twice), those without a year last. Remixes are left out of both and listed in `remixes`, in the same order: titles with "remix", "remixes", "remixed", "reblend", "sped up" or "slowed down" ("Supersonic (Remixes)", "Little L (Sped Up Version)").

### Artist's Popular Songs

Every one of the artist's popular songs, in YouTube Music's order.

```http
GET /api/youtube-music/artist/{artist_id}/songs
```


### Album Tracks

```http
GET /api/youtube-music/album/{album_id}/tracks
```

```json
{
  "album": { "browseId": "MPREb_...", "title": "A Night At The Opera", "artists": [{ "name": "Queen", "id": "UC..." }], "type": "Album", "year": "1975", "thumbnails": [], "trackCount": 12 },
  "tracks": [ { "...": "songs, with trackNumber" } ]
}
```

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
curl -L "http://localhost:5123/api/youtube/preview/fJ9rUzIMcZQ" -o preview.webm

# 3. Add the song and queue its processing (as a session member or logged-in user)
curl -X POST http://localhost:5123/api/songs/from-youtube \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: {session_id}" -H "X-Device-ID: {device_id}" \
  -d '{"video_id": "fJ9rUzIMcZQ", "title": "Bohemian Rhapsody", "artists": [{"name": "Queen"}]}'

# 4. Watch progress via the jobs WebSocket or poll the job
```

---

## Related Documentation

- [Songs API](songs.md) - Creating song records and applying metadata
- [Jobs API](jobs.md) - Tracking download/processing jobs
- [Sessions API](sessions.md) - Session membership for guest downloads
