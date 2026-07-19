# Lyrics API

API documentation for lyrics search, storage, timing analysis, and word-level alignment.

## Base URL

```
/api/lyrics
```

## Overview

Lyrics live in three forms on a song: `plainLyrics` (text), `syncedLyrics` (LRC with line timestamps), and `wordSyncedLyrics` (word-level alignment JSON produced by the alignment pipeline). Updating plain or synced lyrics invalidates any existing word-level alignment.

---

## Search Endpoints

External provider searches — no database writes.

### Search Lyrics (LRCLIB)

```http
GET /api/lyrics/search
```

#### Query Parameters

| Parameter     | Type   | Required | Description            |
|---------------|--------|----------|------------------------|
| `track_name`  | string | Yes      | Song title             |
| `artist_name` | string | Yes      | Artist name            |
| `album_name`  | string | No       | Album name             |

#### Response

A list of LRCLIB results:

```json
[
  {
    "id": 12345,
    "trackName": "Song Title",
    "artistName": "Artist Name",
    "albumName": "Album Name",
    "duration": 245.0,
    "instrumental": false,
    "plainLyrics": "First line...",
    "syncedLyrics": "[00:12.00] First line..."
  }
]
```

### Search Synced Lyrics (syncedlyrics)

Same parameters, searched via the `syncedlyrics` library's multiple providers:

```http
GET /api/lyrics/search-synced
```

---

## Song Lyrics CRUD

### Get Song Lyrics

```http
GET /api/lyrics/songs/{song_id}
```

#### Response

```json
{
  "plainLyrics": "First line...",
  "syncedLyrics": "[00:12.00] First line...",
  "hasAlignment": true
}
```

### Update Song Lyrics

Set plain or synced lyrics. **Requires authentication.** Clears any existing word-level alignment.

```http
POST /api/lyrics/songs/{song_id}?type=synced
```

`type` is `plain` or `synced`.

#### Request Body

```json
{
  "content": "[00:12.00] First line..."
}
```

#### Response

```json
{
  "plainLyrics": "...",
  "syncedLyrics": "[00:12.00] First line..."
}
```

### Clear Song Lyrics

Clear lyrics of a given type (`plain`, `synced`, or `word_synced`). **Requires authentication.** Returns `204 No Content`. Clearing plain or synced lyrics also clears word-level alignment.

```http
DELETE /api/lyrics/songs/{song_id}/{type}
```

---

## Timing Analysis

### Analyze Section Breaks

Analyze synced lyrics for likely instrumental section breaks. Read-only.

```http
GET /api/lyrics/songs/{song_id}/analyze?min_confidence=0.3
```

Returns candidate breaks and a `modified_lrc` preview.

### Apply Section Breaks

Run the same analysis and write the result to `syncedLyrics`. **Requires authentication.**

```http
POST /api/lyrics/songs/{song_id}/analyze/apply?min_confidence=0.3
```

### Analyze Global Offset

Estimate a global timestamp offset of the LRC against the song's separated vocals track. Read-only. Requires `vocals.mp3` to exist (`422` otherwise).

```http
GET /api/lyrics/songs/{song_id}/analyze/offset
```

### Apply Offset Correction

Compute the offset and shift all LRC timestamps accordingly. **Requires authentication.**

```http
POST /api/lyrics/songs/{song_id}/analyze/offset/apply
```

---

## Word-Level Alignment

Alignment runs as a background Celery job and produces `wordSyncedLyrics` (word timings plus instrumental intervals).

### Get Alignment

```http
GET /api/lyrics/songs/{song_id}/alignment
```

#### Response

```json
{
  "alignment": {
    "words": [ { "word": "First", "start": 12.01, "end": 12.35 } ],
    "instrumental_intervals": [ { "start": 0.0, "end": 11.5 } ]
  }
}
```

`alignment` is `null` when no alignment is stored.

### Align Song Lyrics

Enqueue background alignment. May fetch remote lyric candidates and applies offset correction for low-confidence synced lyrics. **Requires authentication.** Requires `vocals.mp3` (`422` otherwise).

```http
POST /api/lyrics/songs/{song_id}/align?language=en&source=plain
```

| Parameter  | Type   | Default | Description                                        |
|------------|--------|---------|----------------------------------------------------|
| `language` | string | `en`    | BCP-47 language code for the alignment model       |
| `source`   | string | —       | Force source: `plain` or `synced` (default: plain-first) |

#### Response

```json
{
  "jobId": "lyrics-align-song-uuid",
  "taskId": "celery-task-id",
  "songId": "song-uuid",
  "status": "pending",
  "dispatched": true,
  "includeRemote": true,
  "source": "plain",
  "language": "en",
  "message": "Lyrics alignment queued."
}
```

If an alignment job is already in flight, the response returns that job with `"dispatched": false`.

### Align From Database Only

Same as above but never fetches remote lyrics — for user-pasted or manually edited lyrics. Returns `404` if the song has no stored lyrics of the requested type.

```http
POST /api/lyrics/songs/{song_id}/align-db?language=en&source=plain
```

---

## Batch Alignment

### Library Alignment Stats

```http
GET /api/lyrics/batch/align
```

#### Response

```json
{
  "total": 150,
  "withVocals": 140,
  "aligned": 90,
  "needsAlignment": 45,
  "noLyrics": 5
}
```

### Run Batch Alignment

Dispatch a Celery task to align songs across the library. **Requires authentication.** Returns `202 Accepted`.

```http
POST /api/lyrics/batch/align?mode=missing&language=en
```

`mode` is `missing` (only unaligned songs) or `all` (re-run everything).

#### Response

```json
{
  "taskId": "celery-task-id",
  "status": "dispatched",
  "mode": "missing",
  "language": "en"
}
```

### Poll Batch Status

```http
GET /api/lyrics/batch/align/status/{task_id}
```

`state` is one of `PENDING`, `STARTED`, `SUCCESS`, `FAILURE`; `SUCCESS` includes a `result` payload.

---

## Usage Examples

```bash
# Search for synced lyrics
curl "http://localhost:5123/api/lyrics/search?track_name=Bohemian+Rhapsody&artist_name=Queen"

# Save synced lyrics to a song
curl -X POST "http://localhost:5123/api/lyrics/songs/{song_id}?type=synced" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{"content": "[00:12.00] Is this the real life?"}'

# Kick off word-level alignment
curl -X POST "http://localhost:5123/api/lyrics/songs/{song_id}/align" \
  -H "Authorization: Bearer {token}"

# Check library-wide alignment status
curl http://localhost:5123/api/lyrics/batch/align
```

---

## Related Documentation

- [Songs API](songs.md) - Lyrics fields on the song object
- [Jobs API](jobs.md) - Tracking alignment jobs
- [Lyrics Analysis System](/lyrics-analysis-system) - How analysis and alignment work internally
