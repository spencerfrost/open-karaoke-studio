# Queue API

Queue operations are session-scoped and separate **upcoming queue order** from **current loaded song state**.

## Base URL

`/api/karaoke-queue`

## Session Requirement

All endpoints require a session code via query param (`session_code`) or header (`X-Session-ID`).

Example header:

```http
X-Session-ID: ABCD
```

---

## Core Semantics

- **Enqueue** (`POST /api/karaoke-queue`): adds to `upcoming` only.
- **Load current** (`POST /api/karaoke-queue/{item_id}/play`): sets a selected queue item as `current` (loaded, paused).
- **Playback commands** (WebSocket performance events): play/pause/seek the current loaded song.

Queue order is represented by `upcoming` positions. `current` is modeled separately.

---

## Endpoints

### `GET /api/karaoke-queue`

Returns explicit queue state:

```json
{
  "current": {
    "id": 7,
    "songId": "song-123",
    "singer": "Alex",
    "position": 0,
    "addedAt": "2026-03-05T12:34:56Z",
    "song": {
      "id": "song-123",
      "title": "Song Title",
      "artist": "Artist",
      "album": "Album",
      "duration": 210.0,
      "coverArt": null,
      "syncedLyrics": null,
      "plainLyrics": null
    }
  },
  "upcoming": [
    {
      "id": 8,
      "songId": "song-456",
      "singer": "Jordan",
      "position": 1,
      "addedAt": "2026-03-05T12:35:20Z",
      "song": {
        "id": "song-456",
        "title": "Next Song",
        "artist": "Another Artist",
        "album": null,
        "duration": 180.0,
        "coverArt": null,
        "syncedLyrics": null,
        "plainLyrics": null
      }
    }
  ],
  "items": [
    {
      "id": 7,
      "songId": "song-123",
      "singer": "Alex",
      "position": 0,
      "addedAt": "2026-03-05T12:34:56Z",
      "song": {
        "id": "song-123",
        "title": "Song Title",
        "artist": "Artist",
        "album": "Album",
        "duration": 210.0,
        "coverArt": null,
        "syncedLyrics": null,
        "plainLyrics": null
      }
    },
    {
      "id": 8,
      "songId": "song-456",
      "singer": "Jordan",
      "position": 1,
      "addedAt": "2026-03-05T12:35:20Z",
      "song": {
        "id": "song-456",
        "title": "Next Song",
        "artist": "Another Artist",
        "album": null,
        "duration": 180.0,
        "coverArt": null,
        "syncedLyrics": null,
        "plainLyrics": null
      }
    }
  ]
}
```

Notes:
- `current` is nullable.
- `upcoming` never includes the current loaded item.
- `items` is retained for compatibility and includes `current` first (if present), then `upcoming`.

### `POST /api/karaoke-queue`

Add song to queue.

Request body:

```json
{
  "songId": "song-123",
  "singer": "Alex"
}
```

Response: created queue item.

### `DELETE /api/karaoke-queue/{item_id}`

Remove a queue item from the session queue.

Response:

```json
{ "success": true }
```

### `PUT /api/karaoke-queue/reorder`

Reorder upcoming queue items.

Request body:

```json
{
  "queue": [
    { "id": 10, "position": 1 },
    { "id": 11, "position": 2 }
  ]
}
```

Response:

```json
{ "success": true }
```

### `POST /api/karaoke-queue/{item_id}/play`

Loads the selected queue item as `current`.

Important:
- This endpoint **loads** the song as current.
- It does **not** automatically start playback.
- Playback starts when host sends WebSocket play command.

Response includes song metadata for current item.

---

## WebSocket Queue Updates

Queue updates are emitted on `/ws/session/{session_id}` as:

```json
{
  "type": "queue_updated",
  "current": { "id": 7, "songId": "song-123", "position": 0 },
  "upcoming": [
    { "id": 8, "songId": "song-456", "position": 1 }
  ],
  "items": [
    { "id": 7, "songId": "song-123", "position": 0 },
    { "id": 8, "songId": "song-456", "position": 1 }
  ]
}
```

Clients should prefer:
- `current` for player song selection
- `upcoming` for queue list rendering

---

## Errors

- `400`: missing/invalid session code
- `404`: session, song, or queue item not found
- `500`: unexpected database/server error

---

## Typical Flow

1. Performer enqueues with `POST /api/karaoke-queue`.
2. Stage sees updated `upcoming` via REST/WS.
3. Host loads item with `POST /api/karaoke-queue/{item_id}/play`.
4. Stage player binds to returned/updated `current`.
5. Host uses playback controls (WS) to start playback.
