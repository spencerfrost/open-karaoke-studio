# Open Karaoke Studio - Architecture

Technical deep-dive into the system architecture, design decisions, and implementation details.

## Table of Contents

1. [System Overview](#system-overview)
2. [Tech Stack](#tech-stack)
3. [Processing Pipeline](#processing-pipeline)
4. [WebSocket Architecture](#websocket-architecture)
5. [Session Management](#session-management)
6. [Database Schema](#database-schema)
7. [API Design](#api-design)
8. [State Management](#state-management)
9. [File Organization](#file-organization)
10. [Critical Design Decisions](#critical-design-decisions)

---

## System Overview

Open Karaoke Studio is a **self-hosted AI-powered karaoke application** designed for small gatherings (5-10 users). The architecture prioritizes:

- **Real-time synchronization** across multiple devices
- **Background audio processing** without blocking UI
- **Session isolation** for multiple concurrent karaoke sessions
- **Simple deployment** (single server, no distributed systems)

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│  React 19 + TypeScript + Vite + Tailwind CSS v4            │
│  TanStack Query + Zustand + React Router                    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ HTTP REST + WebSockets
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                         Backend                              │
│              FastAPI + Uvicorn + SQLAlchemy                 │
└─────────────────┬────────────────┬────────────────┬─────────┘
                  │                │                │
        ┌─────────▼────┐  ┌────────▼──────┐  ┌────▼─────┐
        │ PostgreSQL   │  │ Redis         │  │ Celery   │
        │ (Database)   │  │ (Broker)      │  │ Worker   │
        └──────────────┘  └───────────────┘  └──────────┘
                                                     │
                                            ┌────────▼────────┐
                                            │ yt-dlp + Demucs │
                                            │ Audio Processing│
                                            └─────────────────┘
```

---

## Tech Stack

### Frontend
- **React 19** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS v4** - Styling
- **TanStack Query** - Server state management
- **Zustand** - Client state management
- **React Router** - Routing
- **Shadcn/UI** - Component library
- **React Hook Form + Zod** - Form validation

### Backend
- **FastAPI 2.0** - Web framework
- **Uvicorn** - ASGI server
- **SQLAlchemy** - ORM
- **Alembic** - Database migrations
- **Celery** - Background job queue
- **Redis** - Message broker
- **PostgreSQL** - Database (SQLite for dev)

### Audio Processing
- **yt-dlp** - YouTube downloader
- **Demucs** - AI vocal separation (PyTorch)
- **Audio-Sep** - Roformer model integration
- **librosa** - Audio analysis (BPM detection)

---

## Processing Pipeline

### Flow: YouTube → Karaoke Tracks

```
User Input (YouTube URL + Metadata)
    │
    ├─→ [YouTube Music Search] - Validate & get metadata
    │
    ├─→ [Create Song Record] - Status: "processing"
    │
    ├─→ [Create Job Record] - Link to song
    │
    └─→ [Celery Task: process_youtube_job]
            │
            ├─→ [Phase 1: Download] (0-30% progress)
            │   └─→ yt-dlp downloads audio as original.mp3
            │
            ├─→ [Phase 2: Separation] (30-90% progress)
            │   ├─→ Select engine (Demucs/Roformer/Hybrid)
            │   ├─→ PyTorch processes audio (GPU or CPU)
            │   └─→ Generate vocals.mp3 + instrumental.mp3
            │
            ├─→ [Phase 3: Finalization] (90-100% progress)
            │   ├─→ BPM detection (librosa)
            │   ├─→ Update song record
            │   └─→ Update job status
            │
            └─→ [WebSocket Broadcast] - Notify all clients
```

### Separation Engines

**1. Demucs Standard** ([demucs_standard.py](backend/app/services/separation_engines/demucs_standard.py))
- Model: `htdemucs_ft`
- 2-stem separation (vocals + instrumental)
- Fast, balanced quality
- Default choice

**2. Audio-Sep Roformer** ([audio_sep_roformer.py](backend/app/services/separation_engines/audio_sep_roformer.py))
- Model: Roformer architecture
- Better vocal isolation
- Slower, higher quality
- Good for vocal-focused tracks

**3. Hybrid Sequential** ([hybrid_sequential.py](backend/app/services/separation_engines/hybrid_sequential.py))
- Multi-stage: Roformer → Demucs
- Best quality, slowest
- For critical tracks

**4. Clean Backing** ([clean_backing.py](backend/app/services/separation_engines/clean_backing.py))
- 3-stage advanced processing
- Experimental, highest quality

### File Storage

```
karaoke_library/
  └── {song_id}/
      ├── original.mp3       # Downloaded audio
      ├── vocals.mp3         # Isolated vocals
      └── instrumental.mp3   # Isolated backing track
```

### Performance

- **GPU (CUDA):** 2-5 minutes per song
- **CPU:** 10-20 minutes per song
- **Model Memory:** ~2GB GPU RAM (Demucs)
- **Storage:** ~30-50MB per song (3 files)

---

## WebSocket Architecture

### Critical Design: TWO Endpoints Only

**Why only two?** Simplifies session isolation and prevents global state bugs.

### Endpoint 1: `/ws/jobs` (Global Job Updates)

**Purpose:** Broadcast job processing status to all connected clients

**File:** [jobs.py](backend/app/ws/jobs.py)

**Message Types:**
- `subscribe_to_jobs` - Client subscribes
- `request_jobs_list` - Get current snapshot
- `job_updated` - Progress update (server → clients)
- `job_completed` - Job finished (server → clients)
- `job_failed` - Job error (server → clients)

**Room:** `jobs_updates` (global, not session-specific)

**Connection:**
```
ws://server:5123/ws/jobs
```

---

### Endpoint 2: `/ws/session/{session_id}` (Unified Session)

**Purpose:** All karaoke functionality for a specific session

**File:** [session_specific.py](backend/app/ws/session_specific.py)

**Connection:**
```
ws://server:5123/ws/session/{session_id}?device_id={uuid}
```

**Handles:**
1. **Performance Controls** - Volume, lyrics offset, lyrics size
2. **Player State** - Play/pause, seek, current time
3. **Queue Management** - Queue updates, song changes
4. **Session Lifecycle** - Connection, disconnection, termination

**Message Types:**

**Performance:**
- `update_performance_control` - Client updates setting
- `control_updated` - Broadcast to all (server → clients)
- `join_performance` - Subscribe to performance updates

**Player:**
- `playback_play` - Start playback
- `playback_pause` - Pause playback
- `update_player_state` - Sync player state
- `song_loaded` - New song loaded
- `song_ready` - Audio ready to play

**Queue:**
- `request_queue_update` - Get current queue
- `queue_changed` - Queue modified

**Session:**
- `session_connected` - Connection established
- `session_ended` - Host disconnected

---

### Session State Structure

**Per-session state** (in-memory dictionary keyed by `session_id`):

```python
session_performance_states[session_id] = {
    "vocal_volume": 1.0,          # 0.0 - 2.0 (multiplier)
    "instrumental_volume": 1.0,   # 0.0 - 2.0 (multiplier)
    "lyrics_size": "medium",      # "small", "medium", "large", "x-large"
    "lyrics_offset": 0,           # Milliseconds offset (+/-)
    "current_time": 0,            # Playback position (seconds)
    "duration": 0,                # Track duration (seconds)
    "is_playing": False,          # Playback state
    "current_song_id": None,      # Active song ID
    "is_ready": False,            # Audio loaded & ready
}
```

**CRITICAL:** State is **session-isolated**. Never use global dictionaries.

---

### Connection Manager

**File:** [connection_manager.py](backend/app/ws/connection_manager.py)

**Class:** `SessionConnectionManager`

**Responsibilities:**
- WebSocket lifecycle (connect/disconnect)
- Room-based broadcasting (session isolation)
- Session membership tracking
- Device management (host vs. performer)

**Key Methods:**

```python
# Broadcast to specific session
manager.broadcast_to_room(
    room=f"session_{session_id}",
    message={"type": "queue_updated", ...},
    exclude=[sender_id]  # Don't echo to sender
)

# Join session room
manager.join_session(
    session_id="ABCD",
    device_id="uuid-123",
    device_type="stage"  # or "performer" or "controller"
)
```

---

### Host Disconnect Behavior

**Sequence:**
1. Detect host WebSocket disconnect
2. Acquire session-specific cleanup lock
3. Broadcast `session_ended` to all devices
4. Force close all WebSocket connections
5. Delete session from database (recycle code)
6. Clean up in-memory state: `del session_performance_states[session_id]`

**Why?** Host is authoritative. When host leaves, session is over.

---

## Session Management

### Database Schema

**Table:** `karaoke_sessions`

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER (PK) | Auto-increment ID |
| session_id | VARCHAR(4) | Unique 4-char code (e.g., "ABCD") |
| display_code | VARCHAR(4) | Same as session_id |
| host_device_id | VARCHAR(64) | Host's device UUID |
| created_at | DATETIME | Creation timestamp |
| expires_at | DATETIME | Expiration (default: 24h) |
| is_active | BOOLEAN | Active flag |

**Table:** `session_devices`

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER (PK) | Auto-increment ID |
| session_id | VARCHAR(4) | FK → karaoke_sessions |
| device_id | VARCHAR(64) | Device UUID |
| device_type | VARCHAR(20) | 'stage', 'performer', 'controller' |
| joined_at | DATETIME | Join timestamp |
| is_active | BOOLEAN | Active flag |
| user_agent | TEXT | Browser info |
| display_name | VARCHAR(100) | User's name (optional) |

---

### Session Lifecycle

**1. Create Session**

```
POST /api/sessions
{
  "device_type": "stage",
  "device_id": "uuid-123"
}

Response:
{
  "session_id": "ABCD",
  "display_code": "ABCD",
  "device_id": "uuid-123",
  "is_host": true
}
```

- Generates 4-character code (A-Z, no confusing chars like O/0)
- Creates `KaraokeSession` record
- Sets device as host

**2. Join Session**

```
POST /api/sessions/join/code
{
  "code": "ABCD",
  "device_type": "performer",
  "device_id": "uuid-456"
}

Response:
{
  "session": { ... },
  "is_host": false,
  "devices": [...]
}
```

- Validates session exists & active
- Creates `SessionDevice` record
- Returns session info

**3. WebSocket Connection**

```javascript
const ws = new WebSocket(
  `ws://server/ws/session/ABCD?device_id=uuid-123`
);
```

- Verify session validity
- Check if device is host (`device_id == host_device_id`)
- Join session room: `session_ABCD`
- Send current performance state to joining device

**4. Session Termination**

Triggers:
- Host disconnects (immediate)
- 24-hour expiration (configurable)
- Manual leave (`POST /api/sessions/{session_id}/leave`)

Actions:
- Broadcast `session_ended` to all devices
- Close all WebSocket connections
- Delete session from database
- Clean up in-memory state

---

### Session Isolation Strategy

**Why Session Isolation Matters:**

Multiple karaoke sessions can run simultaneously on the same server. If one session's state affects another, you get:
- Volume changes leaking between sessions
- Queue items appearing in wrong session
- Player state synchronized incorrectly
- Security/privacy issues

**How We Enforce It:**

1. **WebSocket Rooms:** `session_{session_id}` naming
2. **Dictionary Keys:** All in-memory state keyed by `session_id`
3. **Database FK:** `karaoke_queue.session_id` foreign key
4. **API Headers:** `X-Session-ID` header required for queue operations

**Example (Correct):**

```python
# CORRECT - Session-isolated
def get_performance_state(session_id: str):
    return session_performance_states.get(session_id, default_state)

def update_volume(session_id: str, volume: float):
    session_performance_states[session_id]["vocal_volume"] = volume
```

**Example (Wrong - DO NOT DO THIS):**

```python
# WRONG - Global state
global_performance_state = {"vocal_volume": 1.0}  # BAD!

def update_volume(volume: float):
    global_performance_state["vocal_volume"] = volume  # Affects ALL sessions!
```

---

## Database Schema

### Core Tables

**songs** - Song Library

| Column | Type | Description |
|--------|------|-------------|
| id | String (UUID) | Primary key |
| title | String | Song title |
| artist | String | Artist name (default: "Unknown Artist") |
| album | String (nullable) | Album name |
| duration | Float | Duration in seconds |
| date_added | DateTime | When added to library |
| vocals_path | String | Relative path to vocals.mp3 |
| instrumental_path | String | Relative path to instrumental.mp3 |
| original_path | String | Relative path to original.mp3 |
| thumbnail_path | String (nullable) | Artwork path |
| source | String | "youtube" or "upload" |
| source_url | String (nullable) | YouTube URL |
| video_id | String (nullable) | YouTube video ID |
| plain_lyrics | Text (nullable) | Plain text lyrics |
| synced_lyrics | Text (nullable) | LRC format lyrics |
| itunes_track_id | Integer (nullable) | iTunes metadata ID |
| itunes_explicit | Boolean (nullable) | Explicit content flag |
| itunes_preview_url | String (nullable) | 30s preview URL |
| itunes_artwork_urls | Text (nullable) | JSON array of artwork |
| youtube_thumbnail_urls | Text (nullable) | JSON array of thumbnails |
| engine_type | String | "demucs", "roformer", "hybrid" |
| bpm | Float | Beats per minute |
| year | Integer | Release year |
| genre | String (nullable) | Music genre |
| release_date | String (nullable) | Full release date |

**jobs** - Background Processing

| Column | Type | Description |
|--------|------|-------------|
| id | String (UUID) | Primary key |
| filename | String | Job identifier |
| status | String | pending/downloading/processing/finalizing/completed/failed/cancelled |
| progress | Integer | 0-100 |
| status_message | Text (nullable) | Human-readable status |
| task_id | String | Celery task ID |
| song_id | String | FK → songs.id |
| title | String (nullable) | Song title |
| artist | String (nullable) | Artist name |
| created_at | DateTime | Job creation time |
| started_at | DateTime (nullable) | Job start time |
| completed_at | DateTime (nullable) | Job completion time |
| error | Text (nullable) | Error message |
| notes | Text (nullable) | Additional notes |
| dismissed | Boolean | UI dismissal flag |
| engine_type | String | Separation engine used |

**karaoke_queue** - Queue Items

| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Auto-increment ID |
| singer_name | String | Who's singing |
| song_id | String | FK → songs.id |
| position | Integer | Queue order |
| session_id | String | FK → karaoke_sessions.session_id (SESSION ISOLATION!) |
| created_at | DateTime (nullable) | When queued |

---

### Relationships

```
KaraokeSession (1) ←→ (N) SessionDevice
KaraokeSession (1) ←→ (N) KaraokeQueueItem
Song (1) ←→ (N) KaraokeQueueItem
Song (1) ←→ (N) Job
```

**Critical:** Queue items MUST be filtered by `session_id`:

```python
# Get queue for session
queue = db.query(KaraokeQueueItem)\
    .filter(KaraokeQueueItem.session_id == session_id)\
    .order_by(KaraokeQueueItem.position)\
    .all()
```

---

### Repository Pattern

**Files:** `/backend/app/repositories/`

**Purpose:** Separate data access from business logic

**Example:** [song_repository.py](backend/app/repositories/song_repository.py)

```python
class SongRepository:
    def create(self, db: Session, song: Song) -> Song:
        db.add(song)
        db.commit()
        db.refresh(song)
        return song

    def get_by_id(self, db: Session, song_id: str) -> Optional[Song]:
        return db.query(Song).filter(Song.id == song_id).first()

    def delete(self, db: Session, song_id: str):
        db.query(Song).filter(Song.id == song_id).delete()
        db.commit()
```

**Key Feature:** `JobRepository.update()` accepts `skip_events=True` to throttle database writes during high-frequency progress updates.

---

## API Design

### REST Endpoints

**Songs** - `/api/songs`
- `GET /api/songs` - List songs (pagination, search, filter)
- `GET /api/songs/{song_id}` - Get song details
- `POST /api/songs` - Create song (manual upload)
- `PUT /api/songs/{song_id}` - Update metadata
- `DELETE /api/songs/{song_id}` - Delete song + files
- `GET /api/songs/{song_id}/{track_type}` - Stream audio (`vocal`/`instrumental`/`original`)
- `POST /api/songs/{song_id}/reprocess` - Reprocess with different engine

**Sessions** - `/api/sessions`
- `POST /api/sessions` - Create session (host)
- `POST /api/sessions/join/code` - Join by 4-char code
- `POST /api/sessions/join/id` - Join by session ID
- `GET /api/sessions/{session_id}` - Get session info
- `POST /api/sessions/{session_id}/validate` - Check validity
- `POST /api/sessions/{session_id}/leave` - Leave session

**Queue** - `/api/karaoke-queue`
- `GET /api/karaoke-queue` - Get queue (requires `X-Session-ID` header)
- `POST /api/karaoke-queue` - Add song to queue
- `DELETE /api/karaoke-queue/{queue_id}` - Remove from queue
- `PUT /api/karaoke-queue/reorder` - Reorder queue
- `POST /api/karaoke-queue/{queue_id}/play` - Play specific item

**Jobs** - `/api/jobs`
- `GET /api/jobs` - List all jobs
- `GET /api/jobs/{job_id}` - Get job details
- `PUT /api/jobs/{job_id}/dismiss` - Dismiss from UI
- `POST /api/jobs/{job_id}/cancel` - Cancel job (UI only, not implemented)

**YouTube** - `/api/youtube`
- `GET /api/youtube/search` - Search YouTube videos
- `POST /api/youtube/download` - Download & process video

**YouTube Music** - `/api/youtube-music`
- `GET /api/youtube-music/search` - Search YouTube Music (enhanced metadata)

**Lyrics** - `/api/lyrics`
- `POST /api/lyrics/fetch` - Fetch synced lyrics (syncedlyrics)
- `GET /api/lyrics/search` - Search for lyrics online

**Metadata** - `/api/metadata`
- `GET /api/metadata/search` - Search iTunes
- `GET /api/metadata/artwork` - Get artwork URL

---

### API Conventions

**Headers:**
```
X-Session-ID: {session_id}  # Required for queue operations
Content-Type: application/json
```

**Error Responses:**
```json
{
  "detail": "Error message",
  "code": "ERROR_CODE"
}
```

**Pagination:**
```
GET /api/songs?page=1&per_page=50&sort_by=date_added&order=desc
```

**Search:**
```
GET /api/songs/search?q=artist+title&filter_by=artist
```

---

## State Management

### Frontend State Layers

**1. Server State** (TanStack Query)
- Songs, queue, jobs, sessions
- Cached, auto-refetching, optimistic updates
- Managed by [useApiQuery](frontend/src/hooks/useApi.ts), [useApiMutation](frontend/src/hooks/useApi.ts)

**2. Client State** (Zustand)
- Player state ([useKaraokePlayerStore.ts](frontend/src/stores/useKaraokePlayerStore.ts))
- Session state ([sessionStore.ts](frontend/src/stores/sessionStore.ts))
- Processing indicators ([processingIndicatorsStore.ts](frontend/src/stores/processingIndicatorsStore.ts))

**3. Form State** (React Hook Form)
- Form inputs, validation
- Local to form components

**4. URL State** (React Router)
- Current page, route params
- Search params for filters

---

### State Flow Examples

**Adding Song to Queue:**

```
User clicks "Add to Queue"
    ↓
[useSongActions.ts] - Call addToQueueMutation
    ↓
[useApiMutation] - POST /api/karaoke-queue
    ↓
Backend creates queue item
    ↓
Backend broadcasts via WebSocket: {"type": "queue_changed"}
    ↓
Frontend WebSocket receives event
    ↓
[sessionWebSocketService.ts] - Handle queue_changed
    ↓
[TanStack Query] - Invalidate queue cache
    ↓
UI re-renders with updated queue
```

**Volume Control:**

```
User drags volume slider
    ↓
[PerformanceControlsPanel.tsx] - Update local state
    ↓
Send WebSocket: {"type": "update_performance_control", "control": "vocal_volume", "value": 0.5}
    ↓
Backend updates session_performance_states[session_id]
    ↓
Backend broadcasts: {"type": "control_updated", "control": "vocal_volume", "value": 0.5}
    ↓
All other devices receive update
    ↓
[useKaraokePlayerStore] - Update volume
    ↓
Web Audio API applies gain
```

---

## File Organization

### Backend Structure

```
backend/app/
├── api/               # REST endpoints (FastAPI routers)
│   ├── songs.py
│   ├── sessions.py
│   ├── karaoke_queue.py
│   ├── jobs.py
│   ├── youtube.py
│   ├── youtube_music.py
│   ├── lyrics.py
│   └── metadata.py
│
├── ws/                # WebSocket handlers
│   ├── connection_manager.py  # WebSocket lifecycle
│   ├── jobs.py                # Job updates
│   ├── session_specific.py    # Unified session endpoint (CRITICAL)
│   ├── performance.py          # Legacy global endpoint (DEPRECATED)
│   └── queue.py               # Queue helpers
│
├── services/          # Business logic
│   ├── youtube_service.py     # yt-dlp wrapper
│   ├── audio.py               # Audio separation
│   ├── lyrics_service.py      # Lyrics fetching
│   ├── itunes_service.py      # iTunes metadata
│   └── separation_engines/    # Audio processing engines
│       ├── demucs_standard.py
│       ├── audio_sep_roformer.py
│       └── hybrid_sequential.py
│
├── repositories/      # Data access layer
│   ├── song_repository.py
│   └── job_repository.py
│
├── db/                # Database layer
│   ├── database.py            # SQLAlchemy session
│   └── models/                # ORM models
│       ├── song.py
│       ├── job.py
│       ├── session.py
│       └── queue.py
│
├── jobs/              # Celery tasks
│   ├── celery_app.py          # Celery config
│   └── jobs.py                # Task definitions
│
├── schemas/           # Pydantic validation
│   ├── song.py
│   └── youtube.py
│
└── main.py            # FastAPI app entry point
```

### Frontend Structure

```
frontend/src/
├── components/        # Shared UI components
│   ├── layout/            # AppLayout, NavBar
│   ├── player/            # MiniPlayer
│   └── SessionGuard.tsx   # Route protection
│
├── features/          # Feature-based organization
│   ├── library/           # Library browsing
│   ├── lyrics/            # Lyrics system
│   ├── player/            # Main player
│   ├── performance/       # Performance controls
│   ├── queue/             # Queue management
│   ├── session/           # Session management
│   └── songs/             # Song management
│
├── hooks/             # Custom hooks
│   ├── api/               # API hooks (useKaraokeQueue, etc.)
│   ├── useApi.ts          # Base API hooks
│   └── useSessionContext.ts
│
├── stores/            # Zustand stores
│   ├── useKaraokePlayerStore.ts
│   ├── sessionStore.ts
│   └── processingIndicatorsStore.ts
│
├── services/          # External services
│   ├── sessionWebSocketService.ts
│   └── jobsWebSocketService.ts
│
├── pages/             # Page components
│   ├── Library.tsx
│   ├── AddSong.tsx
│   ├── Stage.tsx
│   └── PerformanceControlsPage.tsx
│
└── App.tsx            # Root component
```

---

## Critical Design Decisions

### 1. Session Isolation is Non-Negotiable

**Decision:** All performance/player state uses `session_id` as dictionary key

**Rationale:**
- Multiple karaoke sessions can run simultaneously
- Each session has independent settings (volume, lyrics, queue)
- Host disconnect terminates only their session
- Prevents cross-session bugs and security issues

**Implementation:**
- WebSocket rooms: `session_{session_id}`
- Dictionary keys: `session_performance_states[session_id]`
- Database FK: `karaoke_queue.session_id`

**Trade-off:** More complex state management, but worth it for correctness

---

### 2. Two WebSocket Endpoints Strategy

**Decision:** Split WebSockets into global (`/ws/jobs`) and session-specific (`/ws/session/{id}`)

**Rationale:**
- **Jobs:** Global system events, not session-specific
- **Session:** All karaoke functionality isolated per session
- Prevents global state pollution
- Clean session lifecycle management

**Alternative Considered:** Single unified WebSocket
- **Rejected:** Would require complex routing and session filtering at every message

---

### 3. Client-Side Audio Processing

**Decision:** Volume/pitch/tempo manipulation happens in frontend (Web Audio API)

**Rationale:**
- Backend provides separated tracks (vocals + instrumental)
- Real-time audio effects require low latency
- Streaming audio effects over network would add latency
- Reduces backend complexity and load

**Trade-off:** More frontend complexity, but better user experience

---

### 4. Celery for Background Jobs

**Decision:** Use Celery for audio processing instead of FastAPI background tasks

**Rationale:**
- Audio processing is CPU/GPU intensive (2-20 minutes)
- Need job persistence across server restarts
- Need progress tracking
- Need job cancellation (planned)

**Trade-off:** Extra complexity (Redis broker), but necessary for reliability

**Known Issue:** Celery doesn't hot-reload, requires manual restart

---

### 5. PostgreSQL for Production

**Decision:** PostgreSQL required for production, SQLite for dev only

**Rationale:**
- Concurrent writes (multiple sessions, job updates)
- Better JSON support for metadata
- Production reliability
- Alembic migrations

**Trade-off:** Can't use SQLite for multi-user deployments

---

### 6. Repository Pattern

**Decision:** Separate data access (repositories) from business logic (services)

**Rationale:**
- Testability (mock repositories)
- Reusability (same repository used by API and WebSocket)
- Clear separation of concerns

**Example:**
```
API → Service → Repository → Database
WebSocket → Service → Repository → Database
```

---

### 7. TanStack Query for Server State

**Decision:** Use TanStack Query instead of Redux/Zustand for server state

**Rationale:**
- Automatic caching and refetching
- Optimistic updates out of the box
- Loading/error states handled automatically
- Less boilerplate than Redux

**Trade-off:** Learning curve, but much less code

---

### 8. Feature-Based Frontend Organization

**Decision:** Organize by feature (`features/player/`, `features/lyrics/`) not by type (`components/`, `hooks/`)

**Rationale:**
- Easier to find related code
- Better scalability
- Reduces cognitive load
- Co-location of related files

---

## Architecture Strengths

1. **Clean Separation of Concerns** - API → Services → Repositories → Models
2. **Session Isolation** - Multiple sessions coexist safely
3. **Flexible Audio Engines** - Easy to add new separation algorithms
4. **Real-Time Sync** - WebSockets keep all devices synchronized
5. **Background Processing** - Non-blocking audio processing via Celery
6. **Type Safety** - Pydantic + SQLAlchemy + TypeScript

---

## Architecture Weaknesses

1. **In-Memory WebSocket State** - Not horizontally scalable (single server only)
2. **No Distributed Celery** - Single worker bottleneck
3. **Manual Celery Restart** - Developer experience friction
4. **Client-Side Performance Controls** - Backend doesn't provide pitch/tempo API
5. **PostgreSQL Required** - No lightweight SQLite option for production

---

## Scale Limits

**Designed for:** 5-10 concurrent users

**Why these limits?**
- In-memory WebSocket state (not distributed)
- Single Celery worker (CPU-bound processing)
- PostgreSQL sufficient for small-scale

**Not suitable for:**
- 100+ concurrent users
- Multi-server deployment
- Cloud-scale SaaS

---

## Related Documentation

- [FEATURES.md](FEATURES.md) - What the app can do
- [TECH-DEBT.md](TECH-DEBT.md) - Known issues
- [ROADMAP.md](ROADMAP.md) - Future plans
- [CLAUDE.md](CLAUDE.md) - AI assistant context

---

**Last Updated:** 2026-01-28
