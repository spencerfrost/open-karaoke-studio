# WebSocket Protocol Documentation

This document describes the real-time communication layer for Open Karaoke Studio, using native FastAPI WebSocket endpoints.

## Overview

The application uses **exactly two WebSocket endpoints** for all real-time communication:

| Endpoint | Purpose | File (Backend) | File (Frontend) |
|----------|---------|----------------|-----------------|
| `/ws/jobs` | Global job status updates | `backend/app/ws/jobs.py` | `frontend/src/services/jobsWebSocketService.ts` |
| `/ws/session/{session_id}` | Session-scoped karaoke operations | `backend/app/ws/session_specific.py` | `frontend/src/services/sessionWebSocketService.ts` |

---

## Connection Flow

### Jobs WebSocket (`/ws/jobs`)

1. Client opens WebSocket connection
2. Server sends `{"type": "connected", "status": "connected"}`
3. Client sends `{"type": "subscribe_to_jobs"}`
4. Server responds with current jobs list: `{"type": "jobs_list", "jobs": [...]}`
5. Server broadcasts updates for: `job_created`, `job_updated`, `job_completed`, `job_failed`, `job_cancelled`

### Session WebSocket (`/ws/session/{session_id}`)

1. Client opens WebSocket with optional `?device_id={host_device_id}` query param (host only)
2. Server validates session exists and is active
3. Server sends `{"type": "session_connected", ...}` with current performance state
4. Client sends initial messages to join rooms:
   - `{"type": "join_performance"}`
   - `{"type": "join_queue_room"}`
5. Both host and performer receive real-time updates for their session

---

## Message Catalog

### `/ws/jobs` - Job Broadcasting

#### Server → Client Messages

| Type | Description | Payload |
|------|-------------|---------|
| `connected` | Connection established | `{ status: "connected" }` |
| `subscribed` | Subscription confirmed | `{ status: "subscribed to job updates" }` |
| `jobs_list` | Initial/current jobs snapshot | `{ jobs: JobData[] }` |
| `job_created` | New job added to queue | `{ job: JobData }` |
| `job_updated` | Job progress update | `{ job: JobData }` |
| `job_completed` | Job finished successfully | `{ job: JobData }` |
| `job_failed` | Job encountered error | `{ job: JobData }` |
| `job_cancelled` | Job was cancelled | `{ job: JobData }` |
| `error` | Server error | `{ message: string }` |

#### Client → Server Messages

| Type | Description | Payload |
|------|-------------|---------|
| `subscribe_to_jobs` | Subscribe to updates | none |
| `unsubscribe_from_jobs` | Unsubscribe | none |
| `request_jobs_list` | Request current jobs | none |

#### JobData Interface

```typescript
interface JobData {
  id: string;
  progress?: number;      // 0-100 percentage
  status: string;         // "pending", "downloading", "processing", "completed", "failed", "cancelled"
  error?: string;         // Error message if failed
  notes?: string;         // Additional notes
  created_at?: string;    // ISO timestamp
  started_at?: string;    // ISO timestamp
  completed_at?: string;  // ISO timestamp
  filename?: string;      // Output filename
  task_id?: string;       // Celery task ID
  artist?: string;
  title?: string;
}
```

---

### `/ws/session/{session_id}` - Session Operations

#### Server → Client Messages

##### Connection Events

| Type | Description | Payload |
|------|-------------|---------|
| `session_connected` | New client joined session | `{ session_id, device_id, is_host, performance_state }` |
| `session_error` | Session error occurred | `{ error: string }` |
| `session_ended` | Session terminated | `{ reason: string }` |

##### Performance Control Events

| Type | Description | Payload |
|------|-------------|---------|
| `performance_state` | Current playback state | `{ state: PerformanceState }` |
| `control_updated` | Single control changed | `{ control: string, value: ControlValue }` |

##### Playback Events

| Type | Description | Payload |
|------|-------------|---------|
| `playback_play` | Song started playing | none |
| `playback_pause` | Song paused | none |
| `song_loaded` | Song loaded, ready to play | `{ state: PerformanceState }` |
| `song_ready` | Song fully ready | `{ state: PerformanceState }` |

##### Queue Events

| Type | Description | Payload |
|------|-------------|---------|
| `queue_joined` | Joined queue room | `{ room: string }` |
| `queue_updated` | Queue state changed | `{ current?, upcoming?, items?, trigger? }` |
| `pending_queue_updated` | Pending items changed | `{ pending: QueueItem[] }` |

##### UI Events (Broadcast to Session)

| Type | Description | Payload |
|------|-------------|---------|
| `toggle_fullscreen` | Fullscreen toggle requested | none |

#### Client → Server Messages

##### Connection & State

| Type | Description | Sender | Payload |
|------|-------------|--------|---------|
| `join_performance` | Subscribe to performance state | All | none |
| `join_queue_room` | Subscribe to queue updates | All | none |
| `request_queue_update` | Request current queue | All | none |

##### Performance Controls

| Type | Description | Sender | Payload |
|------|-------------|--------|---------|
| `update_performance_control` | Change a control value | All | `{ control: string, value: ControlValue }` |

##### Playback Controls (Host Only)

| Type | Description | Sender | Payload |
|------|-------------|--------|---------|
| `update_player_state` | Update playback position | Host | `{ isPlaying?, currentTime?, duration? }` |
| `playback_play` | Start playback | Host | none |
| `playback_pause` | Pause playback | Host | none |
| `reset_player_state` | Reset playback | Host | none |
| `song_loaded` | Song loaded | Host | `{ songId, duration, currentTime?, isPlaying? }` |
| `song_ready` | Song ready to play | Host | `{ songId, duration, currentTime?, isPlaying?, isReady? }` |

##### Queue Management

| Type | Description | Sender | Payload |
|------|-------------|--------|---------|
| `toggle_fullscreen` | Request fullscreen toggle | Performer | none |
| `queue_changed` | Notify of external queue change | All | none |

#### TypeScript Interfaces

```typescript
interface PerformanceState {
  vocal_volume: number;           // 0-1
  instrumental_volume: number;    // 0-1
  backing_vocal_volume: number;   // 0-1
  lyrics_size: "small" | "medium" | "large";
  lyrics_offset: number;          // seconds
  current_time: number;           // seconds
  duration: number;               // seconds
  is_playing: boolean;
  current_song_id?: string | null;
  is_ready?: boolean;
  playback_speed?: number;
}

type ControlValue = number | string | boolean;

interface QueueItem {
  id: string;
  songId: string;
  singer: string;
  position: number;
  addedAt?: string;  // ISO timestamp
  song: {
    id: string;
    title: string;
    artist: string;
    album?: string;
    duration?: number;
    syncedLyrics?: string;
    plainLyrics?: string;
  };
}
```

---

## Permission Matrix

| Action | Host | Performer |
|--------|------|-----------|
| `update_performance_control` | ✅ | ✅ |
| `update_player_state` | ✅ | ❌ |
| `playback_play` | ✅ | ❌ |
| `playback_pause` | ✅ | ❌ |
| `song_loaded` | ✅ | ❌ |
| `song_ready` | ✅ | ❌ |
| `reset_player_state` | ✅ | ❌ |
| `join_performance` | ✅ | ✅ |
| `join_queue_room` | ✅ | ✅ |
| `request_queue_update` | ✅ | ✅ |
| `toggle_fullscreen` | ✅ | ✅ |
| `queue_changed` | ✅ | ✅ |

---

## Room Structure

### Jobs Room
- **Room ID**: `jobs_updates`
- **Scope**: Global (all connected clients)
- **Purpose**: Broadcast job status changes to all sessions

### Session Room
- **Room ID**: `session_{session_id}`
- **Scope**: Per-session
- **Purpose**: Isolate session state from other sessions

---

## Error Handling

### Connection Errors

| Code | Meaning |
|------|---------|
| 1000 | Normal closure (client-initiated disconnect) |
| 1008 | Policy violation (invalid session, unauthorized) |

### Client Behavior

- **Reconnect on disconnect**: Clients should attempt to reconnect with exponential backoff (max 30s)
- **Session recovery**: On reconnect, clients re-send `join_performance` and `join_queue_room`
- **Grace period**: Host disconnect triggers 30-second grace period before session termination

---

## Implementation Notes

### Backend

- **Logging**: Use Python `logging` module (not `print()`)
- **State isolation**: All session state keyed by `session_id` in `session_performance_states` dict
- **Persistence**: Player state persisted to `SessionPlaybackState` table on each update

### Frontend

- **Logging**: Use `createLogger("websocket:...")` from `@/lib/logger`
- **Cleanup**: WebSocket cleanup stored in module-private array, not global `window` object
- **Type safety**: Full TypeScript interfaces for all message types

---

## Debugging Tips

1. **Check connection state**: Use `isConnectionActive()` method
2. **Log message flow**: Enable debug logging for `websocket:session` or `websocket:jobs` namespaces
3. **Monitor room membership**: Use `manager.rooms` to see connected clients per room
4. **Session state**: Inspect `session_performance_states[session_id]` for current state

---

## Changelog

| Date | Change |
|------|--------|
| 2026-06-04 | Initial protocol documentation |