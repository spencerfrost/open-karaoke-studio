# Sessions API

API documentation for karaoke session management: creating sessions, joining as a guest, and generating end-of-night playlists.

## Base URL

```
/api/sessions
```

## Overview

A **karaoke session** groups the devices at one gathering: the stage display, the host's controls, and performers' phones. Guests join with a 4-character display code and receive a server-minted `device_id` — their credential for session-member actions (queueing songs, downloading new ones). See [Authentication](authentication.md) for the permission tiers.

Session state is also synchronized in real time over `/ws/session/{session_id}` — see the [WebSocket Protocol](/websocket-protocol).

---

## Endpoints

### Get My Session

Get the host's current active session, or `null` if none exists. **Requires host authentication.**

```http
GET /api/sessions/my
```

#### Response

```json
{
  "session_id": "session-uuid",
  "display_code": "ABCD",
  "device_id": null,
  "is_host": true,
  "device_count": 3,
  "connected_devices": [
    {
      "device_id": "rest_1a2b3c4d5e6f",
      "device_type": "performer",
      "joined_at": "2026-07-12T20:00:00",
      "is_self": false,
      "display_name": "Alex"
    }
  ],
  "created_at": "2026-07-12T19:00:00",
  "expires_at": "2026-07-13T03:00:00",
  "is_active": true
}
```

---

### Get or Create My Session

Get the host's existing active session or create a new one; either way the calling device is registered in it. All devices logged in as the same host share this session. **Requires host authentication.** Returns `201 Created`.

```http
POST /api/sessions/my
```

#### Request Body (optional)

```json
{
  "device_type": "stage",
  "display_name": "Living Room TV"
}
```

`device_type` is one of `stage`, `performer`, `audience` (default `stage`).

Session duration comes from the host's `session_duration_hours` setting (default 8 hours).

#### Response

Same shape as [Get My Session](#get-my-session), with `device_id` set for the calling device.

---

### Create Session

Create a new karaoke session (not tied to a host account's shared session).

```http
POST /api/sessions
```

#### Request Body (optional)

```json
{
  "device_type": "stage",
  "display_name": "Host Name"
}
```

#### Response (`201 Created`)

Same shape as above — includes the new session's `session_id`, `display_code`, and the creating device's `device_id`.

---

### Join Session by Code

Join a session using its 4-character display code. Rate-limited to **10 requests/minute** per IP.

```http
POST /api/sessions/join-by-code
```

#### Request Body

```json
{
  "code": "ABCD",
  "device_type": "performer",
  "display_name": "Alex"
}
```

#### Response

Session info including the minted `device_id` for this device. Save it — `X-Session-ID` + `X-Device-ID` headers authenticate session-member requests.

#### Error Responses

- `400 Bad Request` — Invalid code or device type
- `404 Not Found` — No active session with that code
- `410 Gone` — Session has expired
- `429 Too Many Requests` — Rate limit exceeded

---

### Join Session by ID

Join a session using its full session ID. Rate-limited to **10 requests/minute** per IP.

```http
POST /api/sessions/join-by-id
```

#### Request Body

```json
{
  "session_id": "session-uuid",
  "device_type": "performer",
  "display_name": "Alex"
}
```

#### Error Responses

Same as join-by-code, plus `409 Conflict` if this device already joined the session.

---

### Get Session Info

Get information about a session, including connected devices.

```http
GET /api/sessions/{session_id}/info?device_id={device_id}
```

Pass your `device_id` as a query parameter so the response can correctly mark `is_self` and `is_host`.

#### Error Responses

- `404 Not Found` — Session not found
- `410 Gone` — Session has expired

---

### Validate Session

Lightweight check that a session exists and is active — used before connecting to the WebSocket.

```http
GET /api/sessions/{session_id}/validate
```

#### Response

```json
{
  "valid": true,
  "session_id": "session-uuid",
  "display_code": "ABCD",
  "is_active": true,
  "expires_at": "2026-07-13T03:00:00",
  "created_at": "2026-07-12T19:00:00"
}
```

---

### Leave Session

Leave a session. If the host device leaves, the session is ended.

```http
POST /api/sessions/{session_id}/leave
```

#### Response

```json
{
  "message": "Left session successfully"
}
```

---

## Session Playlist

Generate a YouTube Music playlist from the songs performed during a session.

### Generate Playlist

Trigger playlist generation. Returns `202 Accepted` immediately; poll the GET endpoint for status. Idempotent — repeat calls return the existing generation's status.

```http
POST /api/sessions/{session_id}/playlist
```

#### Response

```json
{
  "status": "pending",
  "youtube_music_url": null,
  "youtube_music_playlist_id": null,
  "song_count": 0,
  "error_message": null,
  "created_at": "2026-07-13T02:00:00+00:00",
  "completed_at": null
}
```

`status` is one of `pending`, `processing`, `ready`, `failed`.

### Get Playlist Status

```http
GET /api/sessions/{session_id}/playlist
```

Returns the same shape; when `status` is `ready`, `youtube_music_url` links to the created playlist. Returns `404` if generation was never started.

---

## Usage Examples

```bash
# Host: get or create the shared session
curl -X POST http://localhost:5123/api/sessions/my \
  -H "Authorization: Bearer {host-token}" \
  -H "Content-Type: application/json" \
  -d '{"device_type": "stage"}'

# Guest: join with the 4-character code
curl -X POST http://localhost:5123/api/sessions/join-by-code \
  -H "Content-Type: application/json" \
  -d '{"code": "ABCD", "device_type": "performer", "display_name": "Alex"}'

# Validate before opening the WebSocket
curl http://localhost:5123/api/sessions/{session_id}/validate

# After the party: generate the YouTube Music playlist
curl -X POST http://localhost:5123/api/sessions/{session_id}/playlist
curl http://localhost:5123/api/sessions/{session_id}/playlist
```

---

## Related Documentation

- [Queue API](queue.md) - Session-scoped queue operations
- [Authentication API](authentication.md) - Permission tiers and headers
- [WebSocket Protocol](/websocket-protocol) - Real-time session sync
- [Demo Accounts](/demo-accounts) - Demo session behavior
