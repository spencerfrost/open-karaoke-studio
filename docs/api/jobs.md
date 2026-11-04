# Jobs API

Complete API documentation for background job management and monitoring.

## Base URL

```
/api/jobs
```

## Overview

The Jobs API manages background processing tasks for audio separation, YouTube downloads, and other long-running operations. Jobs are processed asynchronously using Celery workers and updates are broadcast via WebSocket.

**All Jobs API endpoints require an admin account.** They cover every session's jobs, and host accounts include the public demo ones. Guests and the stage follow their own jobs over `/ws/jobs` instead.

## Job Status Values

| Status        | Description                                  |
|--------------|----------------------------------------------|
| `pending`    | Job queued, waiting to start                 |
| `downloading`| Downloading audio from YouTube               |
| `processing` | Audio separation in progress                 |
| `finalizing` | Completing processing, saving files          |
| `completed`  | Job finished successfully                    |
| `failed`     | Job encountered an error                     |
| `cancelled`  | Job was cancelled                            |

## Job Steps

`step` says which part of the pipeline a job is on. It's separate from `status`, which says whether
the job is waiting, running or done. While a job is `pending`, its step is the one it's waiting for.

| Step       | Description                                                     |
|------------|-----------------------------------------------------------------|
| `download` | Downloading audio from YouTube                                  |
| `separate` | AI vocal/instrumental separation                                |
| `align`    | Lyrics alignment. Runs as its own job (`engine_type: "lyrics_alignment"`), so its step is always `align` |

## Job Fields

Every endpoint and WebSocket message serializes jobs the same way. A job never carries the session
ID (the session's join code) or the user that started it. In their place it has `owner_tag`, an
opaque per-session tag: an HMAC-SHA256 of the session ID keyed with `SECRET_KEY`, truncated to 16
hex characters. A device compares it with `owner_tag` on its [session response](sessions.md) to
tell which jobs its session started. Jobs started outside a session have `null`.

## Endpoints

### Get Job Status Overview

Get aggregate statistics about all jobs in the system.

```http
GET /api/jobs/status
```

#### Response

```json
{
  "total": 45,
  "pending": 2,
  "processing": 1,
  "completed": 40,
  "failed": 2,
  "cancelled": 0
}
```

---

### List All Jobs

Get a list of all jobs with optional filtering.

```http
GET /api/jobs
```

#### Query Parameters

| Parameter          | Type    | Default | Description                              |
|-------------------|---------|---------|------------------------------------------|
| `status`          | string  | None    | Filter by status (see status values above) |

#### Response

```json
{
  "jobs": [
    {
      "id": "job-uuid",
      "song_id": "song-uuid",
      "task_id": "celery-task-id",
      "filename": "song_file_identifier",
      "title": "Song Title",
      "artist": "Artist Name",
      "status": "processing",
      "progress": 65,
      "status_message": "Separating vocals...",
      "engine_type": "demucs",
      "created_at": "2026-01-28T10:00:00",
      "started_at": "2026-01-28T10:00:05",
      "completed_at": null,
      "error": null,
      "step": "separate",
      "owner_tag": "3f9a1c0e7b2d4a68"
    }
  ]
}
```

---

### Get Job Details

Get detailed information about a specific job. `expected_completion` is only present while the job is `processing`.

```http
GET /api/jobs/{job_id}
```

#### Path Parameters

| Parameter | Type   | Description |
|-----------|--------|-------------|
| `job_id`  | string | Job UUID    |

#### Response

```json
{
  "id": "job-uuid",
  "song_id": "song-uuid",
  "task_id": "celery-task-id",
  "filename": "song_file_identifier",
  "title": "Song Title",
  "artist": "Artist Name",
  "status": "processing",
  "progress": 65,
  "status_message": "Separating vocals with Demucs...",
  "engine_type": "demucs",
  "created_at": "2026-01-28T10:00:00Z",
  "started_at": "2026-01-28T10:00:05Z",
  "completed_at": null,
  "error": null,
  "step": "separate",
  "owner_tag": "3f9a1c0e7b2d4a68",
  "expected_completion": "2026-01-28T10:03:00"
}
```

#### Error Responses

- `404 Not Found` - Job doesn't exist

```json
{
  "detail": "Job not found"
}
```

---

### Cancel Job

Attempt to cancel a running or pending job.

```http
POST /api/jobs/{job_id}/cancel
```

#### Path Parameters

| Parameter | Type   | Description |
|-----------|--------|-------------|
| `job_id`  | string | Job UUID    |

#### Response

```json
{
  "success": true,
  "message": "Job cancelled",
  "job_id": "job-uuid"
}
```

Cancelling revokes the underlying Celery task (`SIGTERM`) and marks the job as cancelled. Jobs that are already `completed`, `failed`, or `cancelled` return `400 Bad Request`.

**Note:** New processing jobs are created through the source-specific endpoints — [YouTube download](youtube.md) or [Reprocess Song](songs.md#reprocess-song) — not through the Jobs API itself.

---

## Job Progress Phases

Audio processing jobs go through distinct phases with specific progress ranges:

| Phase              | Progress Range | Description                           |
|-------------------|----------------|---------------------------------------|
| **Download**      | 0-30%          | Downloading audio from YouTube        |
| **Separation**    | 30-90%         | AI vocal/instrumental separation      |
| **Finalization**  | 90-100%        | Saving files, updating metadata       |

### Status Messages by Phase

**Download Phase:**
- "Downloading audio from YouTube..."
- "Download complete"

**Separation Phase:**
- "Separating vocals with Demucs..."
- "Separating vocals with Roformer..."
- "Running hybrid separation..."
- "Processing audio (XX%)"

**Finalization Phase:**
- "Finalizing audio files..."
- "Detecting BPM..."
- "Saving metadata..."
- "Processing complete"

**Error States:**
- "Download failed: {error}"
- "Separation failed: {error}"
- "Processing error: {error}"

---

## WebSocket Integration

Jobs broadcast real-time updates via the `/ws/jobs` WebSocket endpoint.

### WebSocket Events

**Subscribe to Job Updates:**
```json
{
  "type": "subscribe_to_jobs"
}
```

**Request Current Jobs List:**
```json
{
  "type": "request_jobs_list"
}
```

**Server Broadcasts:**

Every broadcast wraps one job in the shape shown above. The full catalog is in the
[WebSocket Protocol](/websocket-protocol#ws-jobs-job-broadcasting).

```json
{
  "type": "job_updated",
  "job": {
    "id": "job-uuid",
    "song_id": "song-uuid",
    "status": "processing",
    "step": "separate",
    "progress": 45,
    "status_message": "Separating: Model 1/2",
    "owner_tag": "3f9a1c0e7b2d4a68"
  }
}
```

The other broadcasts are `job_created`, `job_completed`, `job_failed` and `job_cancelled`, each
with the same `job` payload. `jobs_list` (`{"type": "jobs_list", "jobs": [...]}`) lists the
in-flight jobs (`pending`, `downloading`, `processing`) that belong to a song.

`/ws/jobs` admits any account or session member (its first message must be `authenticate`; see
[WebSocket Protocol](../websocket-protocol.md#jobs-websocket-ws-jobs)). Every session shares the
feed, which is why job payloads carry `owner_tag` rather than the join code.

---

## Separation Engines

When creating jobs, different audio separation engines can be used:

| Engine          | Speed    | Quality | Use Case                           |
|----------------|----------|---------|-------------------------------------|
| `three_track`  | Medium   | Best    | Default; vocals + backing vocals + instrumental |
| `demucs`       | Fast     | Good    | Balanced quality/speed              |
| `roformer`     | Medium   | Better  | Better vocal isolation              |
| `hybrid`       | Slow     | Best    | Multi-stage, highest quality        |
| `clean_backing`| Slowest  | Best    | Experimental, 3-stage processing    |

**Performance (approximate):**
- **GPU:** 2-5 minutes per song
- **CPU:** 10-20 minutes per song

---

## Error Codes

| Error Code                | HTTP Status | Description                    |
|--------------------------|-------------|--------------------------------|
| `RESOURCE_NOT_FOUND`     | 404         | Job doesn't exist              |
| `DATABASE_ERROR`         | 500         | Database operation failed      |
| `SERVICE_ERROR`          | 500         | Job service error              |
| `AUDIO_PROCESSING_ERROR` | 500         | Audio separation failed        |
| `NETWORK_ERROR`          | 502         | YouTube download failed        |

---

## Usage Examples

### Monitor Job Progress

```bash
# Get all active jobs
curl "http://localhost:5123/api/jobs?status=processing"

# Get specific job details
curl http://localhost:5123/api/jobs/job-uuid

# Get job statistics
curl http://localhost:5123/api/jobs/status
```

### Manage Jobs

```bash
# Cancel a job
curl -X POST http://localhost:5123/api/jobs/job-uuid/cancel
```

### WebSocket Connection (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:5123/ws/jobs');

ws.onopen = () => {
  // Subscribe to job updates
  ws.send(JSON.stringify({
    type: 'subscribe_to_jobs'
  }));
  
  // Request current jobs
  ws.send(JSON.stringify({
    type: 'request_jobs_list'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'job_updated':
      console.log(`Job ${data.job.id} (${data.job.step}): ${data.job.progress}%`);
      break;
    case 'job_completed':
      console.log(`Job ${data.job.id} completed!`);
      break;
    case 'job_failed':
      console.error(`Job ${data.job.id} failed: ${data.job.error}`);
      break;
  }
};
```

---

## Related Documentation

- [Songs API](songs.md) - Song management endpoints
- [Ingestion & Processing Pipeline](/domains/ingestion-pipeline) - Audio processing details
- [Error Handling Guide](error-handling.md) - Error codes and handling
