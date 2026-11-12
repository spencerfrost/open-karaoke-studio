# Lyrics API

API documentation for lyrics search, storage, timing analysis, and word-level alignment.

## Base URL

```
/api/lyrics
```

## Overview

Lyrics live in three forms on a song: `plainLyrics` (text), `syncedLyrics` (LRC with line timestamps), and `wordSyncedLyrics` (word-level alignment JSON produced by the alignment pipeline). Updating plain or synced lyrics invalidates any existing word-level alignment.

Every read needs an account or session-member credential (see [Authentication](authentication.md)). The provider searches are rate limited at `20/minute` per client IP, and the two alignment endpoints, which each start a GPU job, at `10/minute`. Listing, resolving and undoing lyrics reports, and listing lyrics feedback, is admin-only.

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

### List Languages

```http
GET /api/lyrics/languages
```

Account or session-member credential. Returns the language codes a song's lyrics language can be
set to: every language Whisper knows (`["en", "zh", "de", …]`).

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

## Lyrics Reports

Anyone singing can report that a song's lyrics are wrong. A report records what was on screen and
queues alignment to try a fix; see [Lyrics System § Reports](/domains/lyrics-system#reports-someone-singing-says-the-lyrics-are-wrong).

### Report a Song's Lyrics

```http
POST /api/lyrics/songs/{song_id}/reports
```

Account or session-member credential.

```json
{ "kind": "words" }
```

`kind` is `words` (the text is wrong) or `timing` (the words are right but out of sync). Reports are
merged per song, kind and lyrics text: reporting again bumps `reportCount`. A `words` report on
hand-picked lyrics clears `lyrics_hand_picked_at`, so other sources may replace them. When the song
has a vocals stem, alignment is queued.

```json
{
  "report": {
    "id": 7,
    "songId": "…",
    "title": "Hate Me",
    "artist": "Blue October",
    "kind": "words",
    "reportCount": 2,
    "reporterName": "Sam",
    "createdAt": "2026-10-28T21:40:00",
    "lastReportedAt": "2026-10-28T22:15:00",
    "outcome": null,
    "resolved": false,
    "lyricsSource": "lrclib:1",
    "lyricsHandPicked": false,
    "canRestore": true
  },
  "alignment": {
    "jobId": "…",
    "taskId": "…",
    "songId": "…",
    "status": "pending",
    "dispatched": true,
    "includeRemote": true,
    "source": null,
    "language": null,
    "message": "Lyrics alignment queued."
  }
}
```

`alignment` is the same object `POST …/align` returns; `dispatched` is `false` when a run for the
song was already queued or running. `404` for an unknown song, `422` when the song has no lyrics. `alignment` is `null` without a
vocals stem. `outcome` is filled in once the alignment run finishes: `replaced`, `retimed`,
`transcribed` or `unchanged`.

### List Open Reports

```http
GET /api/lyrics/reports
```

Admin only. Open reports, most recently reported first, each shaped like `report` above.

### Resolve a Report

```http
POST /api/lyrics/reports/{report_id}/resolve
```

Admin only. Marks the report dealt with and returns it. Lyrics reported as wrong stay rejected, so
alignment won't pick that text again. `404` for an unknown report.

### Undo a Report

```http
POST /api/lyrics/reports/{report_id}/undo
```

Admin only. "The report was wrong": restores the reported text (marked hand-picked), deletes the
report, which lifts the rejection, and re-aligns.

```json
{ "restored": true, "alignment": { "jobId": "…", "status": "pending", "dispatched": true, … } }
```

---

## Lyrics Feedback

After each song the stage asks "How were the lyrics?". Answers fix nothing; they record which songs need work and which are right.

### Answer for a Finished Song

```http
POST /api/lyrics/feedback
```

Needs an account or session-member credential for the queue item's session. The song must still be the session's queue item (it is until the next song starts) and must have lyrics. Answering again for the same queue item replaces the answer.

#### Request

```json
{ "queue_item_id": 41, "rating": "way_off" }
```

`rating` is `spot_on`, `a_bit_off` or `way_off`.

#### Response

```json
{ "queueItemId": 41, "rating": "way_off" }
```

`404` when the queue item is gone, `403` for someone outside its session, `422` when the song has no lyrics or the rating is unknown.

### List Feedback by Song

```http
GET /api/lyrics/feedback
```

Admin only. One entry per song with answers, worst first: most `wayOff`, then most `aBitOff`, then most `plays`.

#### Response

```json
[
  {
    "songId": "…",
    "title": "Hate Me",
    "artist": "Blue October",
    "spotOn": 0,
    "aBitOff": 1,
    "wayOff": 2,
    "earlier": 1,
    "plays": 6,
    "lastAnsweredAt": "2026-10-28T22:15:00",
    "lyricsSource": "lrclib:1",
    "lyricsHandPicked": false
  }
]
```

`spotOn`, `aBitOff` and `wayOff` count answers about the lyrics and word timings the song shows now. `earlier` counts answers about lyrics or timings it has since replaced, so a fixed song drops to zero. `plays` counts the song's performance history rows.

## Batch Alignment

### Library Alignment Stats

```http
GET /api/lyrics/batch/align
```

**Requires an admin account.**

#### Response

```json
{
  "total": 150,
  "withVocals": 140,
  "aligned": 90,
  "needsAlignment": 45,
  "noLyrics": 5,
  "repair": 12,
  "repairReasons": {
    "no_word_timing": 8,
    "plain_only": 2,
    "plain_timing": 1,
    "words_mismatch": 1,
    "reported": 1
  }
}
```

`repair` counts the songs a `repair` run would queue; a song can have more than one reason.

### Run Batch Alignment

Runs go through the `lyrics_alignment` batch job (modes `missing`, `repair`, `all`): see [Admin API](admin.md).

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

# Check library-wide alignment status (admin)
curl http://localhost:5123/api/lyrics/batch/align \
  -H "Authorization: Bearer {token}"
```

---

## Related Documentation

- [Songs API](songs.md) - Lyrics fields on the song object
- [Jobs API](jobs.md) - Tracking alignment jobs
- [Lyrics System](/domains/lyrics-system) - How lyrics, alignment, reports and feedback work internally
- [Lyrics Analysis](/lyrics-analysis-system) - The thinking behind section breaks and offset detection
