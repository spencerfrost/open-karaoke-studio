# Queue API

Complete API documentation for real-time karaoke queue management.

## Base URL

```
/api/karaoke-queue
```

## Overview

The Queue API manages the karaoke song queue for active sessions. All queue operations are **session-isolated**, meaning each karaoke session has its own independent queue. Queue changes are broadcast in real-time to all connected devices in the session via WebSocket.

## Session Requirement

All queue endpoints require the `X-Session-ID` header to identify which session's queue to operate on.

```http
X-Session-ID: ABCD
```

**Important:** Queue operations without a valid session ID will fail.

---

## Endpoints

### Get Queue

Get the current queue for a session.

```http
GET /api/karaoke-queue
```

#### Headers

| Header        | Type   | Required | Description      |
|--------------|--------|----------|------------------|
| `X-Session-ID`| string | Yes      | Session code (4 chars) |

#### Response

```json
{
  "queue": [
    {
      "id": 1,
      "singer_name": "John",
      "position": 0,
      "created_at": "2026-01-28T10:00:00Z",
      "song": {
        "id": "song-uuid",
        "title": "Song Title",
        "artist": "Artist Name",
        "album": "Album Name",
        "duration": 245.5,
        "thumbnail_path": "song-uuid/thumbnail.jpg",
        "vocals_path": "song-uuid/vocals.mp3",
        "instrumental_path": "song-uuid/instrumental.mp3"
      }
    },
    {
      "id": 2,
      "singer_name": "Sarah",
      "position": 1,
      "created_at": "2026-01-28T10:05:00Z",
      "song": {
        "id": "song-uuid-2",
        "title": "Another Song",
        "artist": "Another Artist",
        "duration": 180.0
      }
    }
  ],
  "session_id": "ABCD"
}
```

**Note:** Queue items are returned in order by `position` (ascending). Position 0 is the currently playing song.

---

### Add to Queue

Add a song to the queue for the current session.

```http
POST /api/karaoke-queue
```

#### Headers

| Header        | Type   | Required | Description      |
|--------------|--------|----------|------------------|
| `X-Session-ID`| string | Yes      | Session code     |

#### Request Body

```json
{
  "song_id": "song-uuid",
  "singer_name": "John Doe"
}
```

#### Response

```json
{
  "id": 3,
  "singer_name": "John Doe",
  "position": 2,
  "song_id": "song-uuid",
  "session_id": "ABCD",
  "created_at": "2026-01-28T10:10:00Z",
  "message": "Song added to queue"
}
```

**Side Effects:**
- WebSocket broadcast to all session members with `queue_changed` event
- Queue position automatically assigned (appends to end)

---

### Remove from Queue

Remove a specific item from the queue.

```http
DELETE /api/karaoke-queue/{queue_id}
```

#### Path Parameters

| Parameter  | Type    | Description           |
|-----------|---------|------------------------|
| `queue_id`| integer | Queue item ID          |

#### Headers

| Header        | Type   | Required | Description      |
|--------------|--------|----------|------------------|
| `X-Session-ID`| string | Yes      | Session code     |

#### Response

```json
{
  "message": "Queue item removed successfully",
  "queue_id": 3
}
```

**Side Effects:**
- Remaining items automatically reordered
- WebSocket broadcast to all session members

---

### Reorder Queue

Reorder queue items to new positions.

```http
PUT /api/karaoke-queue/reorder
```

#### Headers

| Header        | Type   | Required | Description      |
|--------------|--------|----------|------------------|
| `X-Session-ID`| string | Yes      | Session code     |

#### Request Body

Array of queue items with their new positions:

```json
{
  "items": [
    {
      "id": 2,
      "position": 0
    },
    {
      "id": 1,
      "position": 1
    },
    {
      "id": 3,
      "position": 2
    }
  ]
}
```

#### Response

```json
{
  "message": "Queue reordered successfully",
  "updated_count": 3
}
```

**Side Effects:**
- All specified items moved to new positions
- WebSocket broadcast to all session members

---

### Play Specific Item

Move a specific queue item to position 0 (play immediately).

```http
POST /api/karaoke-queue/{queue_id}/play
```

#### Path Parameters

| Parameter  | Type    | Description           |
|-----------|---------|------------------------|
| `queue_id`| integer | Queue item ID          |

#### Headers

| Header        | Type   | Required | Description      |
|--------------|--------|----------|------------------|
| `X-Session-ID`| string | Yes      | Session code     |

#### Response

```json
{
  "message": "Song moved to play position",
  "queue_id": 5,
  "new_position": 0
}
```

**Side Effects:**
- Selected item moved to position 0
- Other items shifted down
- WebSocket broadcast triggers playback start on connected clients

---

## WebSocket Integration

Queue changes are broadcast via the `/ws/session/{session_id}` WebSocket endpoint.

### WebSocket Events

**Request Queue Update:**
```json
{
  "type": "request_queue_update"
}
```

**Server Broadcasts:**

**Queue Changed:**
```json
{
  "type": "queue_changed",
  "session_id": "ABCD",
  "queue": [
    {
      "id": 1,
      "singer_name": "John",
      "position": 0,
      "song": {
        "id": "song-uuid",
        "title": "Song Title",
        "artist": "Artist Name"
      }
    }
  ]
}
```

**Song Loaded:**
```json
{
  "type": "song_loaded",
  "session_id": "ABCD",
  "song_id": "song-uuid",
  "queue_id": 1
}
```

---

## Session Isolation

**Critical:** All queue operations are scoped to a specific session using the `X-Session-ID` header.

### Why Session Isolation?

Multiple karaoke sessions can run simultaneously on the same server. Session isolation ensures:
- Each session has its own independent queue
- Queue changes only affect that session's devices
- No cross-session contamination

### How It Works

1. Client includes `X-Session-ID: ABCD` header in all requests
2. Backend filters queue queries by `session_id = 'ABCD'`
3. WebSocket broadcasts only to devices in session `session_ABCD` room

**Example (Wrong - No Session ID):**
```bash
# This will fail
curl http://localhost:5123/api/karaoke-queue
# Error: Missing session header
```

**Example (Correct - With Session ID):**
```bash
# This works
curl http://localhost:5123/api/karaoke-queue \
  -H "X-Session-ID: ABCD"
```

---

## Queue Position Rules

### Position Numbering

- Position is **0-indexed**
- Position `0` is the **currently playing** song
- Position `1` is **next up**
- Maximum position = queue length - 1

### Auto-Positioning

When adding a song without specifying position:
- New item automatically appended to end
- Position = current max position + 1

### Reordering Rules

When reordering:
- All items must have unique positions
- Positions must be consecutive (0, 1, 2, 3...)
- Missing items keep their current position

---

## Error Codes

| Error Code            | HTTP Status | Description                     |
|----------------------|-------------|---------------------------------|
| `MISSING_SESSION_ID` | 400         | X-Session-ID header missing     |
| `INVALID_SESSION`    | 404         | Session doesn't exist           |
| `RESOURCE_NOT_FOUND` | 404         | Queue item doesn't exist        |
| `VALIDATION_ERROR`   | 400         | Invalid request data            |
| `DATABASE_ERROR`     | 500         | Database operation failed       |

---

## Usage Examples

### Basic Queue Operations

```bash
# Get current queue (with session header)
curl http://localhost:5123/api/karaoke-queue \
  -H "X-Session-ID: ABCD"

# Add song to queue
curl -X POST http://localhost:5123/api/karaoke-queue \
  -H "X-Session-ID: ABCD" \
  -H "Content-Type: application/json" \
  -d '{
    "song_id": "abc-def-123",
    "singer_name": "John Doe"
  }'

# Remove from queue
curl -X DELETE http://localhost:5123/api/karaoke-queue/5 \
  -H "X-Session-ID: ABCD"
```

### Queue Management

```bash
# Move song to play immediately
curl -X POST http://localhost:5123/api/karaoke-queue/7/play \
  -H "X-Session-ID: ABCD"

# Reorder queue
curl -X PUT http://localhost:5123/api/karaoke-queue/reorder \
  -H "X-Session-ID: ABCD" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"id": 3, "position": 0},
      {"id": 1, "position": 1},
      {"id": 2, "position": 2}
    ]
  }'
```

### WebSocket Integration (JavaScript)

```javascript
const sessionId = 'ABCD';
const ws = new WebSocket(`ws://localhost:5123/ws/session/${sessionId}`);

ws.onopen = () => {
  // Request current queue
  ws.send(JSON.stringify({
    type: 'request_queue_update'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'queue_changed':
      console.log('Queue updated:', data.queue);
      updateQueueUI(data.queue);
      break;
      
    case 'song_loaded':
      console.log('Now playing:', data.song_id);
      startPlayback(data.song_id);
      break;
  }
};
```

---

## Common Workflows

### Adding Song to Queue

1. User selects song from library
2. Frontend calls `POST /api/karaoke-queue` with `X-Session-ID` header
3. Backend adds song to session's queue
4. Backend broadcasts `queue_changed` via WebSocket
5. All devices in session update their queue display

### Playing Next Song

1. Current song ends
2. Frontend calls `POST /api/karaoke-queue/{next_id}/play`
3. Backend moves item to position 0
4. Backend broadcasts `song_loaded` via WebSocket
5. All devices start playback of new song

### Queue Reordering

1. User drags queue item to new position (frontend)
2. Frontend calls `PUT /api/karaoke-queue/reorder` with new order
3. Backend updates all positions atomically
4. Backend broadcasts `queue_changed` via WebSocket
5. All devices reflect new order

---

## Related Documentation

- [Sessions API](../sessions.md) - Session management
- [Songs API](songs.md) - Song management
- [Architecture: Session Management](../ARCHITECTURE.md#session-management) - Session architecture details
- [Architecture: WebSocket](../ARCHITECTURE.md#websocket-architecture) - Real-time communication
- [Error Handling Guide](error-handling.md) - Error codes and handling
