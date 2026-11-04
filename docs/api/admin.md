# Admin API

Endpoints behind the admin dashboard's **Overview**, **Background jobs**, **Failed songs** and **Compare breaks** pages. All of them are **admin only**.

A batch job works through the whole library one song (or artist, or album) at a time on the `enrichment` Celery queue. Every run is recorded in the `batch_runs` table: the API creates the row as `queued` when a run is requested, and the task moves it to `running`, counts `done` / `failed` after each song, and closes it.

| Kind | What it does | Modes |
|------|--------------|-------|
| `duration` | Song length from the original audio | `missing`, `all` |
| `loudness` | EBU R128 loudness and playback gain | `missing`, `all` |
| `singing_map` | When the lead and backing vocals are singing, from the stems | `missing`, `all` |
| `vocal_range` | Lowest and highest sung note | `missing`, `all` |
| `song_albums` | Finds each song's album and cover on YouTube Music (exact video), else Deezer. Skips hand-set albums; deletes albums left unlinked when it ends | `missing`, `all` |
| `fingerprint` | AcoustID fingerprint; links the MusicBrainz recording, or suggests a different name for review | `missing`, `retry` |
| `artist_images` | Discogs artist photos | `missing` |
| `lyrics_alignment` | Queues one `align_song_lyrics` job per song | `missing`, `repair`, `all` |
| `artist_credits` | Re-credits every song from its MusicBrainz recording (older songs without one are re-parsed), merges duplicate artists, fixes names, deletes unused artists; saves a report | `preview`, `apply` |

`missing` runs on the rows that don't have the result yet; `all` re-runs every row. Fingerprinting has no `all`: AcoustID never renames a song, so re-asking about matched or hand-confirmed songs gains nothing. Its `retry` re-asks about songs AcoustID couldn't settle (ambiguous, no match, or a failed lookup), unless a person confirmed their title and artist; an ambiguous song is linked when one of the tied recordings is named like it. Lyrics alignment's run only *queues* songs (each aligns as its own job), so its progress after that shows in its coverage. Artist credits runs over the whole library in both modes: `preview` makes every change in one transaction and rolls it back, `apply` commits it, and both save the same report. Its coverage counts songs credited from a list (their credits keep the name each was printed as); take a `pg_dump` before `apply`.

The three hand-run scans (`GET /api/songs/library-audit`, `/metadata-audit`, `/duplicates`) run inside their request, and each writes one finished row to `batch_runs` (kind `disk_check`, `metadata_scan` or `duplicates`) with `total` (what it looked at) and `issues` (what it found), so the overview can show the last result without scanning again. Scan rows stay out of the jobs list and its recent runs.

---

### Overview

```http
GET /api/admin/overview
```

Counts for the admin landing page. Nothing here scans the library, so the page polls it (every 3 seconds while a batch run is active, every 30 otherwise).

#### Response

```json
{
  "librarySize": 1471,
  "needsYou": {
    "lyricsReports": 2,
    "acoustid": { "suggested": 12, "ambiguous": 218, "noMatch": 102, "failed": 20 },
    "failedSongs": 5,
    "alignmentRepair": 860
  },
  "jobs": [
    { "kind": "loudness", "coverage": { "have": 1, "of": 1476 }, "activeRun": null }
  ],
  "songsAdded": {
    "weeks": [{ "start": "2026-07-17", "count": 2 }],
    "recent": [
      { "id": "…", "title": "Golden Hour", "artist": "JVKE", "status": "processing", "dateAdded": "2026-10-09T20:14:03Z" }
    ]
  },
  "scans": {
    "disk_check": null,
    "metadata_scan": { "id": 31, "kind": "metadata_scan", "status": "done", "total": 1476, "issues": 17, "finishedAt": "2026-10-07T21:02:11Z" },
    "duplicates": null
  }
}
```

- `librarySize` counts songs guests can see (everything but failed ones).
- `needsYou.alignmentRepair` is the lyrics alignment job's `repair` count, as on the jobs page.
- `jobs` has every batch job's coverage and its queued or running run, the same as [List Jobs](#list-jobs) without the mode counts.
- `songsAdded.weeks` is 12 weeks, oldest first, counting back from now, so the last is the past seven days. `recent` is the six newest songs, any status.
- `scans` is each scan's last finished run (a run object, trimmed above), or `null` if it has never run.

### List Jobs

```http
GET /api/admin/jobs
```

Before answering, any `running` row that hasn't reported progress for 15 minutes is closed as `failed` (its worker died).

#### Response

```json
{
  "jobs": [
    {
      "kind": "loudness",
      "modes": ["missing", "all"],
      "coverage": { "have": 1488, "of": 1500 },
      "modeCounts": { "missing": 12, "all": 1500 },
      "lastRun": { "id": 7, "kind": "loudness", "mode": "missing", "status": "done", "total": 40, "done": 39, "failed": 1, "error": null, "createdAt": "2026-10-09T18:02:11Z", "startedAt": "2026-10-09T18:02:12Z", "finishedAt": "2026-10-09T18:03:40Z" },
      "activeRun": null
    }
  ]
}
```

`lyrics_alignment` also has `repairReasons`: how many songs needing repair have each reason (see [Lyrics API](lyrics.md#library-alignment-stats)).

Run `status` is `queued`, `running`, `done`, `failed` or `cancelled`. `total` is `null` until the task has selected its rows. `hasReport` is `true` on a finished run of a job that saves a report.

### Recent Runs

```http
GET /api/admin/jobs/runs?limit=20
```

Runs of every job, newest first, as `{ "runs": [...] }`. `limit` is 1–100.

### Run a Job

```http
POST /api/admin/jobs/{kind}/run?mode=missing
```

Returns `202` with `{ "run": {...} }`. Errors: `404` unknown kind, `400` a mode the job doesn't have, `409` the job already has a queued or running run, `503` the Celery broker can't be reached (the run is recorded as failed).

### Run Report

```http
GET /api/admin/jobs/runs/{run_id}/report
```

The report a run saved, as `{ "run": {...}, "report": {...} }`; `404` if it has none. The artist credits report has `before` and `after` (library counts), `songs` (`counts` by source and `changed`: each song's credits before → after, confirmed songs marked), `merges`, `renames`, `deleted`, `unsure` (songs without a recording whose primary artist has "&" or "and") and `disagree` (songs whose credits don't name the artist in their text). Lists stop at 2,000 rows; counts are always whole.

### Stop a Run

```http
POST /api/admin/jobs/runs/{run_id}/cancel
```

Marks the run `cancelled` and revokes its task. A queued task never starts; a running one stops before its next song. `409` if the run already finished.

### Worker Status

```http
GET /api/admin/workers
```

Asks the Celery workers which queues they serve (1 second timeout).

```json
{
  "brokerReachable": true,
  "workers": ["audio@box", "enrichment@box"],
  "queues": [
    { "queue": "audio", "workers": ["audio@box"] },
    { "queue": "enrichment", "workers": ["enrichment@box"] },
    { "queue": "lyrics", "workers": [] }
  ]
}
```

A queue with no workers means its jobs wait until one starts.

### Failed Songs

```http
GET /api/admin/songs/failed
```

Songs with `status: "error"`: their download or processing failed, and the songbook hides them. Each is a full song object, most recent failure first. `errorMessage` says why; `failedAt` is when, in UTC without a zone marker, or `null` for songs that failed before failures were timed.

To restart one from its own video, use `POST /api/songs/{id}/retry`; to give it a different source, `POST /api/songs/{id}/replace-youtube`.

### Compare breaks

```http
GET /api/admin/singing-map/songs
GET /api/admin/singing-map/songs/{song_id}
PUT /api/admin/singing-map/songs/{song_id}/checks
```

Instrumental breaks worked out from the singing map, next to the breaks the TV shows today (gaps between aligned words). Nothing here changes what the TV shows.

The list has every processed song with synced lyrics (without them there are no bars): songs with moments still to check first, most disagreement first among them, songs not measured yet last. `tally` counts every answer about the moments songs show now:

```json
{
  "songs": [
    {
      "songId": "a27fb804-…",
      "title": "Anna Molly",
      "artist": "Incubus",
      "measured": true,
      "hasWordTiming": true,
      "wordGapBreaks": 3,
      "mapBreaks": 3,
      "disagreements": 1,
      "toCheck": 1,
      "answers": ["map_right", "bar_fine"]
    }
  ],
  "tally": { "map_right": 41, "today_right": 6, "bar_fine": 4 }
}
```

`disagreements` counts breaks only one method found, or both found with an end more than 1.5 s apart; `mapBreaks` and `disagreements` are `null` until the song is measured. `toCheck` counts moments not answered yet, leaving out breaks both methods agree on.

One song measures its map first if it has none (a second or two) and saves it; a song with no vocals track is `409`. The response has the map (`lead`, `backing` as `[start, end]` lists, `backing` `null` without a backing track, `duration`, `measuredAt`, `params`), `backingOnScreen` (backing singing while a lyric line is on screen), `lines` (each non-blank LRC line's `index`, `start`, `end`, `text`, and `timed` when the times come from word timing), `mapBreaks` and `wordGapBreaks` in the player's `instrumental_intervals` shape, and `moments` in song order:

```json
[
  { "kind": "break", "start": 0.0, "end": 39.4, "map": [0.0, 39.38], "wordGaps": [0.0, 39.5], "agree": true, "key": "break:0.00-39.38:0.00-39.50", "answer": null },
  { "kind": "backing_only", "start": 132.0, "end": 158.0, "onScreen": true, "lineText": "Wait, there is a light", "key": "backing:132.00-158.00", "answer": "lyrics_match" }
]
```

A moment's `key` is built from its exact times, so re-measuring with other settings gives a moved moment a new key and no answer, while unchanged moments keep theirs.

`PUT …/checks` answers moments by ear, as `{"answers": [{"key": "…", "answer": "map_right"}]}`; `"answer": null` clears one. A break takes `map_right`, `today_right`, `both_wrong` or `either_fine`; backing singing with no lyrics on screen `bar_fine` or `no_bar`; with lyrics on screen `lyrics_match` or `lyrics_dont_match`. All or nothing: a key the song no longer shows, or an answer that doesn't fit its moment, is a `400` and saves nothing. Each answer is a `break_checks` row, one per song and moment key, holding the moment and the map's settings as they were. Returns the song as `GET` does.
